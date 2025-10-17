import os
import pandas as pd
import yfinance as yf
import sqlite3
from datetime import datetime

DB_PATH = "Database/stock_history.db"

def init_db(db_path=DB_PATH):
    """Initialize the SQLite database with tables for prices and dividends."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Historical prices table
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
            PRIMARY KEY (ticker, date)
        )
    """)
    # Dividends table
    c.execute("""
        CREATE TABLE IF NOT EXISTS dividends (
            ticker TEXT,
            date TEXT,
            dividend REAL,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.commit()
    conn.close()

EUR_SUFFIXES = [".AS", ".PA", ".DE", ".MC"]
GBP_SUFFIXES = [".L", ".LN"]

def is_eur_ticker(ticker):
    return any(ticker.endswith(suffix) for suffix in EUR_SUFFIXES)

def is_gbp_ticker(ticker):
    return any(ticker.endswith(suffix) for suffix in GBP_SUFFIXES)

def get_eurusd_rates(start, end):
    fx = yf.Ticker("EURUSD=X")
    fx_hist = fx.history(start=start, end=end)
    return fx_hist["Close"]

def get_gbpusd_rates(start, end):
    fx = yf.Ticker("GBPUSD=X")
    fx_hist = fx.history(start=start, end=end)
    return fx_hist["Close"]

def get_max_date_for_ticker(ticker, db_path=DB_PATH):
    """Get the maximum date for a ticker in the database."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT MAX(date) FROM prices WHERE ticker = ?", (ticker,))
    result = c.fetchone()
    conn.close()
    return result[0] if result[0] else None

def save_prices_and_dividends(ticker_list, db_path=DB_PATH, period="max"):
    conn = sqlite3.connect(db_path)
    for ticker in ticker_list:
        print(f"Fetching data for {ticker}...")
        try:
            # Check if ticker already has data in database
            max_date = get_max_date_for_ticker(ticker, db_path)
            
            if max_date:
                # Only fetch data after the max date
                from datetime import datetime, timedelta
                start_date = (datetime.strptime(max_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                print(f"  Fetching data from {start_date} onwards for {ticker}")
                data = yf.Ticker(ticker)
                hist = data.history(start=start_date)
            else:
                # New ticker, fetch all data
                print(f"  New ticker {ticker}, fetching all available data")
                data = yf.Ticker(ticker)
                hist = data.history(period=period)
            if not hist.empty:
                if is_eur_ticker(ticker):
                    print(f"  Converting {ticker} prices to USD...")
                    fx_rates = get_eurusd_rates(hist.index.min(), hist.index.max())
                    fx_rates = fx_rates.reindex(hist.index, method='ffill')
                    for col in ["Open", "High", "Low", "Close"]:
                        hist[col] = hist[col] * fx_rates
                elif is_gbp_ticker(ticker):
                    print(f"  Converting {ticker} prices to USD...")
                    fx_rates = get_gbpusd_rates(hist.index.min(), hist.index.max())
                    fx_rates = fx_rates.reindex(hist.index, method='ffill')
                    for col in ["Open", "High", "Low", "Close"]:
                        hist[col] = hist[col] * fx_rates
                
                price_records = [
                    (
                        ticker,
                        idx.strftime("%Y-%m-%d"),
                        row.get("Open", None),
                        row.get("High", None),
                        row.get("Low", None),
                        row.get("Close", None),
                        row.get("Adj Close", row.get("Close", None)),
                        row.get("Volume", None)
                    )
                    for idx, row in hist.iterrows()
                ]
                conn.executemany("""
                    INSERT OR REPLACE INTO prices
                    (ticker, date, open, high, low, close, adj_close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, price_records)
                print(f"  Added {len(price_records)} price records for {ticker}")
            else:
                print(f"  No new price data available for {ticker}")
            
            # Save dividends (only fetch if we have new price data or it's a new ticker)
            if not hist.empty or not max_date:
                div = data.dividends
                if not div.empty:
                    # Filter dividends to only include new ones if we have existing data
                    if max_date:
                        div = div[div.index > max_date]
                    
                    if not div.empty:
                        dividend_records = [
                            (ticker, idx.strftime("%Y-%m-%d"), val)
                            for idx, val in div.items()
                        ]
                        conn.executemany("""
                            INSERT OR REPLACE INTO dividends
                            (ticker, date, dividend)
                            VALUES (?, ?, ?)
                        """, dividend_records)
                        print(f"  Added {len(dividend_records)} dividend records for {ticker}")
                    else:
                        print(f"  No new dividend data available for {ticker}")
                else:
                    print(f"  No dividend data available for {ticker}")
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Example: Load tickers from Excel file
    tickers_file = "Stock Selection/tickers_used.xlsx"
    if os.path.exists(tickers_file):
        tickers_df = pd.read_excel(tickers_file)
        tickers = tickers_df["Ticker"].dropna().unique().tolist()
        print(f"Loaded {len(tickers)} tickers from {tickers_file}")
    else:
        tickers = ["AAPL", "MSFT"]  # fallback example
        print(f"Using fallback tickers: {tickers}")

    print("Initializing database...")
    init_db()
    
    print("Starting incremental price update...")
    print("This will only fetch data that's missing from the database.")
    print("-" * 50)
    
    save_prices_and_dividends(tickers)
    
    print("-" * 50)
    print("Database update complete.")