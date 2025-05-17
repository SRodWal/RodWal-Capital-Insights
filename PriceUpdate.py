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

def save_prices_and_dividends(ticker_list, db_path=DB_PATH, period="max"):
    """Download and store historical prices and dividends for a list of tickers."""
    conn = sqlite3.connect(db_path)
    for ticker in ticker_list:
        print(f"Fetching data for {ticker}...")
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period=period)
            # Save prices
            if not hist.empty:
                # Use .get() to avoid KeyError if 'Adj Close' is missing
                price_records = [
                    (
                        ticker,
                        idx.strftime("%Y-%m-%d"),
                        row.get("Open", None),
                        row.get("High", None),
                        row.get("Low", None),
                        row.get("Close", None),
                        row.get("Adj Close", row.get("Close", None)),  # fallback to Close if Adj Close missing
                        row.get("Volume", None)
                    )
                    for idx, row in hist.iterrows()
                ]
                conn.executemany("""
                    INSERT OR REPLACE INTO prices
                    (ticker, date, open, high, low, close, adj_close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, price_records)
            # Save dividends
            div = data.dividends
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
    else:
        tickers = ["AAPL", "MSFT"]  # fallback example

    init_db()
    save_prices_and_dividends(tickers)
    print("Database update complete.")