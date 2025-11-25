import os
import pandas as pd
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta, date
import time
import random

DB_PATH = "Database/stock_history.db"

# ---------------------------
# Market / currency heuristics
# ---------------------------
EUR_SUFFIXES = [".AS", ".PA", ".DE", ".MC", ".MI"]  # Euronext, Paris, Xetra, Spain, Milan
GBP_SUFFIXES = [".L", ".LN"]                        # London
USD_QUOTED_STOCKS = ["SGLD.L", "SDIA.L", "NDIA.L"]  # Exceptions quoted in USD

def is_eur_ticker(ticker: str) -> bool:
    return any(ticker.endswith(suffix) for suffix in EUR_SUFFIXES)

def is_gbp_ticker(ticker: str) -> bool:
    return any(ticker.endswith(suffix) for suffix in GBP_SUFFIXES)

def is_usdquoted_ticker(ticker: str) -> bool:
    return ticker in USD_QUOTED_STOCKS

def infer_currency_from_symbol(ticker: str) -> str:
    """Fast heuristic for quoted currency to avoid network calls when possible."""
    if is_usdquoted_ticker(ticker):
        return "USD"
    if is_eur_ticker(ticker):
        return "EUR"
    if is_gbp_ticker(ticker):
        return "GBP"
    # US tickers and most others we track: default USD
    return "USD"

def get_ticker_currency_safe(ticker: str) -> str:
    """
    Determine the quoted currency.
    Try heuristic first; fall back to yfinance (fast_info) if ambiguous.
    """
    cur = infer_currency_from_symbol(ticker)
    if cur != "USD":
        return cur
    try:
        fi = yf.Ticker(ticker).fast_info  # faster than .info
        yf_cur = fi.get("currency")
        if isinstance(yf_cur, str) and len(yf_cur) in (3, 4):  # e.g., "USD"
            return yf_cur
    except Exception:
        pass
    return cur

# ---------------------------
# DB utilities
# ---------------------------
def retry_db_operation(func, max_retries=3, delay=1):
    """Retry database operations with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"  Database locked, retrying in {wait_time:.1f}s... "
                      f"(attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise
        except Exception:
            raise

def table_exists(conn, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None

def column_exists(conn, table_name: str, column_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1].lower() for row in cur.fetchall()]
    return column_name.lower() in cols

def ensure_prices_currency_column(db_path=DB_PATH):
    """Add 'currency' column to prices if missing."""
    def _alter():
        with sqlite3.connect(db_path) as conn:
            if table_exists(conn, "prices") and not column_exists(conn, "prices", "currency"):
                conn.execute("ALTER TABLE prices ADD COLUMN currency TEXT")
                conn.commit()
    retry_db_operation(_alter)

def migrate_lowercase_fx_to_FX_Rates(db_path=DB_PATH):
    """If old 'fx_rates' exists and 'FX_Rates' is empty, copy over."""
    def _migrate():
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            has_fx_lower = table_exists(conn, "fx_rates")
            has_fx_camel = table_exists(conn, "FX_Rates")
            if not has_fx_camel:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS FX_Rates (
                        pair TEXT,
                        date TEXT,
                        rate REAL,
                        PRIMARY KEY (pair, date)
                    )
                """)
                conn.commit()
                has_fx_camel = True

            if has_fx_lower and has_fx_camel:
                # Check if FX_Rates is empty
                cur.execute("SELECT COUNT(*) FROM FX_Rates")
                cnt = cur.fetchone()[0]
                if cnt == 0:
                    print("Migrating existing 'fx_rates' data into 'FX_Rates'...")
                    cur.execute("INSERT OR IGNORE INTO FX_Rates (pair, date, rate) SELECT pair, date, rate FROM fx_rates")
                    conn.commit()
    retry_db_operation(_migrate)

def init_db(db_path=DB_PATH):
    """Initialize or upgrade the DB for prices, dividends, and FX_Rates."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def _init():
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()

            # Prices with currency column
            c.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    ticker TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    adj_close REAL,
                    volume INTEGER,
                    currency TEXT,
                    PRIMARY KEY (ticker, date)
                )
            """)

            # Dividends unchanged
            c.execute("""
                CREATE TABLE IF NOT EXISTS dividends (
                    ticker TEXT,
                    date TEXT,
                    dividend REAL,
                    PRIMARY KEY (ticker, date)
                )
            """)

            # New FX_Rates (CamelCase as requested)
            c.execute("""
                CREATE TABLE IF NOT EXISTS FX_Rates (
                    pair TEXT,
                    date TEXT,
                    rate REAL,
                    PRIMARY KEY (pair, date)
                )
            """)
            conn.commit()

    retry_db_operation(_init)

    # Ensure upgrades on existing DBs
    ensure_prices_currency_column(db_path)
    migrate_lowercase_fx_to_FX_Rates(db_path)

def get_max_date_for_ticker(ticker, db_path=DB_PATH):
    """Get the max stored price date for a ticker."""
    def _get():
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(date) FROM prices WHERE ticker = ?", (ticker,))
            res = cur.fetchone()
            return res[0] if res and res[0] else None
    return retry_db_operation(_get)

def get_max_date_for_pair(pair, db_path=DB_PATH):
    """Get the max stored FX date for a pair in FX_Rates."""
    def _get():
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(date) FROM FX_Rates WHERE pair = ?", (pair,))
            res = cur.fetchone()
            return res[0] if res and res[0] else None
    return retry_db_operation(_get)

# ---------------------------
# FX updaters (global, not per ticker)
# ---------------------------
PAIR_TO_YF = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
}

def fetch_fx_series(pair: str, start: str | None, end: str | None):
    yf_symbol = PAIR_TO_YF[pair]
    fx = yf.Ticker(yf_symbol)
    if start:
        hist = fx.history(start=start, end=end)
    else:
        hist = fx.history(period="max")
    if hist.empty:
        return []
    close_series = hist["Close"]
    return [(pair, idx.strftime("%Y-%m-%d"), float(val)) for idx, val in close_series.items()]

def update_fx_rates(pairs=("EURUSD", "GBPUSD"), db_path=DB_PATH):
    """Incrementally update FX_Rates for the specified pairs."""
    today_str = (date.today()+ timedelta(days = 1)).strftime("%Y-%m-%d")
    total = 0
    for pair in pairs:
        try:
            max_date = get_max_date_for_pair(pair, db_path)
            if max_date:
                # fetch from next day after max_date
                start_dt = (datetime.strptime(max_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                print(f"Updating {pair} from {start_dt} to {today_str}...")
                rows = fetch_fx_series(pair, start=start_dt, end=today_str)
            else:
                print(f"Initializing {pair} with full history...")
                rows = fetch_fx_series(pair, start=None, end=None)

            if rows:
                def _save():
                    with sqlite3.connect(db_path) as conn:
                        conn.executemany("""
                            INSERT OR REPLACE INTO FX_Rates (pair, date, rate) VALUES (?, ?, ?)
                        """, rows)
                        conn.commit()
                retry_db_operation(_save)
                print(f"  Added {len(rows)} {pair} FX records")
                total += len(rows)
            else:
                print(f"  No new FX data for {pair}")
        except Exception as e:
            print(f"Error updating FX for {pair}: {e}")
        time.sleep(0.3)

    print(f"FX update complete. Total FX rows added: {total}")

# ---------------------------
# Prices & Dividends
# ---------------------------
def save_prices_and_dividends(ticker_list, db_path=DB_PATH, period="max"):
    """
    Save prices and dividends for each ticker.
    - Prices are stored as quoted (no USD conversion).
    - Adds 'currency' column value per ticker.
    """
    for ticker in ticker_list:
        print(f"Fetching data for {ticker}...")
        try:
            ticker_obj = yf.Ticker(ticker)

            # Incremental start
            max_date = get_max_date_for_ticker(ticker, db_path)
            if max_date:
                start_date = (datetime.strptime(max_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                print(f"  Fetching prices from {start_date} onwards")
                hist = ticker_obj.history(start=start_date)
            else:
                print(f"  New ticker {ticker}, fetching all available price history")
                hist = ticker_obj.history(period=period)

            if not hist.empty:
                # Determine currency once per ticker
                quoted_currency = get_ticker_currency_safe(ticker)

                price_records = [
                    (
                        ticker,
                        idx.strftime("%Y-%m-%d"),
                        float(row.get("Open", float("nan"))) if row.get("Open", None) is not None else None,
                        float(row.get("High", float("nan"))) if row.get("High", None) is not None else None,
                        float(row.get("Low", float("nan"))) if row.get("Low", None) is not None else None,
                        float(row.get("Close", float("nan"))) if row.get("Close", None) is not None else None,
                        float(row.get("Adj Close", row.get("Close", float("nan")))) if row.get("Adj Close", None) is not None or row.get("Close", None) is not None else None,
                        int(row.get("Volume", 0)) if row.get("Volume", None) is not None else None,
                        quoted_currency
                    )
                    for idx, row in hist.iterrows()
                ]

                def _save_prices():
                    with sqlite3.connect(db_path) as conn:
                        conn.executemany("""
                            INSERT OR REPLACE INTO prices
                            (ticker, date, open, high, low, close, adj_close, volume, currency)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, price_records)
                        conn.commit()
                retry_db_operation(_save_prices)
                print(f"  Added {len(price_records)} price records for {ticker}")
            else:
                print(f"  No new price data available for {ticker}")

            # Dividends (keep as-is; stored in original currency implicitly)
            # If we fetched no new prices but ticker is new, still try dividends
            if (not hist.empty) or (not max_date):
                div = ticker_obj.dividends
                if not div.empty:
                    if max_date:
                        div = div[div.index > max_date]
                    if not div.empty:
                        dividend_records = [
                            (ticker, idx.strftime("%Y-%m-%d"), float(val))
                            for idx, val in div.items()
                        ]
                        def _save_dividends():
                            with sqlite3.connect(db_path) as conn:
                                conn.executemany("""
                                    INSERT OR REPLACE INTO dividends
                                    (ticker, date, dividend)
                                    VALUES (?, ?, ?)
                                """, dividend_records)
                                conn.commit()
                        retry_db_operation(_save_dividends)
                        print(f"  Added {len(dividend_records)} dividend records for {ticker}")
                    else:
                        print("  No new dividend data available")
                else:
                    print("  No dividend data available")
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            continue

        time.sleep(0.5)  # small delay to avoid rate limits / DB contention

# ---------------------------
# Entry point
# ---------------------------
if __name__ == "__main__":
    # Load tickers from Excel
    tickers_file = "Stock Selection/tickers_used.xlsx"
    if os.path.exists(tickers_file):
        tickers_df = pd.read_excel(tickers_file)
        tickers = tickers_df["Ticker"].dropna().unique().tolist()
        print(f"Loaded {len(tickers)} tickers from {tickers_file}")
    else:
        tickers = ["AAPL", "MSFT"]  # fallback
        print(f"Using fallback tickers: {tickers}")

    print("Initializing database...")
    init_db()

    print("Starting incremental price update...")
    print("This will only fetch data that's missing from the database.")
    print(f"Processing {len(tickers)} tickers...")
    print("-" * 50)

    start_time = time.time()
    save_prices_and_dividends(tickers)

    print("-" * 50)
    print("Updating global FX rates (EURUSD, GBPUSD)...")
    update_fx_rates(pairs=("EURUSD", "GBPUSD"))

    end_time = time.time()
    print("-" * 50)
    print(f"Database update complete. Total time: {end_time - start_time:.1f} seconds")