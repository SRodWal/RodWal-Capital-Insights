
"""
Update Alpha Vantage income statements (annual & quarterly) into SQLite.

- Creates tables if missing
- Upserts rows on (symbol, fiscalDateEnding, metric)
- Light backoff on rate-limit or transient errors

Author: Samuel R. Walton / RodWal
"""

import os
import time
import sqlite3
from typing import Iterable, Optional, Tuple

import pandas as pd
import requests

import plotly.graph_objects as go


# --- Internal configurations (adjust to your project) ---
try:
    # If you already have these in core.config, import them
    from core.config import AVantage_API_KEY, AVantage_url  # Avantage_funcs not required here
except Exception:
    AVantage_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "TF28ZZDMC9JZOOA7")
    AVantage_url = "https://www.alphavantage.co/query"

DB_PATH = "Database/stock_history.db"

# ---------- SQLite helpers ----------
def ensure_db_and_tables(db_path: str) -> sqlite3.Connection:
    """Create the database directory and required tables if they do not exist."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS income_statements_annual (
            symbol TEXT NOT NULL,
            fiscalDateEnding TEXT NOT NULL,
            reportedCurrency TEXT,
            metric TEXT NOT NULL,
            value REAL,
            loaded_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (symbol, fiscalDateEnding, metric)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS income_statements_quarterly (
            symbol TEXT NOT NULL,
            fiscalDateEnding TEXT NOT NULL,
            reportedCurrency TEXT,
            metric TEXT NOT NULL,
            value REAL,
            loaded_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (symbol, fiscalDateEnding, metric)
        );
        """
    )

    conn.commit()
    return conn


def upsert_df(
    conn: sqlite3.Connection,
    table: str,
    df: pd.DataFrame,
) -> Tuple[int, int]:
    """
    Upsert a melted dataframe into the target table.
    Returns (inserted_or_updated_rows, total_rows_attempted).
    """
    if df.empty:
        return 0, 0

    # Normalize types
    df = df.copy()
    # Try to cast numeric values; keep None for non-convertible
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    rows = [
        (
            row["symbol"],
            row["fiscalDateEnding"],
            row.get("reportedCurrency"),
            row["metric"],
            None if pd.isna(row["value"]) else float(row["value"]),
            None,  # loaded_at -> default now
        )
        for _, row in df.iterrows()
    ]

    sql = f"""
        INSERT INTO {table} (symbol, fiscalDateEnding, reportedCurrency, metric, value, loaded_at)
        VALUES (?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
        ON CONFLICT(symbol, fiscalDateEnding, metric) DO UPDATE SET
            reportedCurrency = excluded.reportedCurrency,
            value = excluded.value,
            loaded_at = excluded.loaded_at;
    """
    cur = conn.cursor()
    cur.executemany(sql, rows)
    conn.commit()
    return cur.rowcount, len(rows)


# ---------- Alpha Vantage fetch ----------
class AVClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = AVantage_url,
        timeout: int = 20,
        session: Optional[requests.Session] = None,
    ):
        if not api_key:
            raise ValueError("Alpha Vantage API key is missing.")
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.session = session or requests.Session()

    def fetch_income_statement(
        self, symbol: str, max_retries: int = 3, sleep_seconds: float = 2.0
    ) -> dict:
        """
        Fetch income statements for a symbol.
        Returns the raw JSON dict (expects keys: symbol, annualReports, quarterlyReports).
        """
        params = {
            "function": "INCOME_STATEMENT",
            "symbol": symbol,
            "apikey": self.api_key,
        }

        for attempt in range(1, max_retries + 1):
            resp = self.session.get(self.base_url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                # Retry on HTTP errors
                time.sleep(sleep_seconds * attempt)
                continue

            data = resp.json()

            # Common error payloads from Alpha Vantage
            if "Note" in data or "Information" in data or "Error Message" in data:
                # Backoff and retry (rate limit / invalid symbol / etc.)
                time.sleep(sleep_seconds * attempt)
                continue

            return data

        raise RuntimeError(
            f"Failed to fetch income statement for {symbol} after {max_retries} attempts."
        )


def melt_reports(reports: list, symbol: str) -> pd.DataFrame:
    """
    Melt Alpha Vantage report list (one row per metric per period).
    Keeps 'fiscalDateEnding' and 'reportedCurrency' as id_vars.
    """
    if not reports:
        return pd.DataFrame(columns=["symbol", "fiscalDateEnding", "reportedCurrency", "metric", "value"])

    df = pd.DataFrame(reports)
    # Keep these identifiers; everything else becomes 'metric' -> 'value'
    id_vars = [c for c in ["fiscalDateEnding", "reportedCurrency"] if c in df.columns]
    melted = df.melt(id_vars=id_vars, var_name="metric", value_name="value")
    melted["symbol"] = symbol
    return melted

# ---------- Orchestration ----------
def update_income_statements_for_symbol(
    symbol: str,
    db_path: str = DB_PATH,
    api_key: str = AVantage_API_KEY,
    base_url: str = AVantage_url,
) -> Tuple[int, int]:
    """
    Fetch and persist annual & quarterly income statements for a single symbol.
    Returns (rows_upserted, total_rows_attempted).
    """
    conn = ensure_db_and_tables(db_path)
    client = AVClient(api_key=api_key, base_url=base_url)

    payload = client.fetch_income_statement(symbol)

    symbol_returned = payload.get("symbol", symbol)
    annual_df = melt_reports(payload.get("annualReports", []), symbol_returned)
    quarterly_df = melt_reports(payload.get("quarterlyReports", []), symbol_returned)

    upserted_a, attempted_a = upsert_df(conn, "income_statements_annual", annual_df)
    upserted_q, attempted_q = upsert_df(conn, "income_statements_quarterly", quarterly_df)

    conn.close()
    return (upserted_a + upserted_q), (attempted_a + attempted_q)


def update_income_statements_for_list(
    symbols: Iterable[str],
    db_path: str = DB_PATH,
    api_key: str = AVantage_API_KEY,
    base_url: str = AVantage_url,
    pause_seconds: float = 1.5,  # gentle pacing; adjust to your plan
) -> dict:
    """
    Batch updater for multiple symbols. Returns a dict of per-symbol stats.
    """
    stats = {}
    for i, sym in enumerate(symbols, start=1):
        try:
            upserted, attempted = update_income_statements_for_symbol(
                sym, db_path=db_path, api_key=api_key, base_url=base_url
            )
            stats[sym] = {"attempted": attempted, "upserted": upserted, "status": "ok"}
        except Exception as e:
            stats[sym] = {"attempted": 0, "upserted": 0, "status": f"error: {e}"}
        # light pacing between calls
        time.sleep(pause_seconds)
    return stats

### GRAPHS


import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio



DB_PATH = "Database/stock_history.db"
ANNUAL_TABLE = "income_statements_annual"
QUARTERLY_TABLE = "income_statements_quarterly"

# Ensure our template is registered

from module_styles import register_bloomberg_like_template, human_biz, apply_business_ticks
BLOOMBERG_TMPL = register_bloomberg_like_template()

def _load_revenue(symbol: str):
    with sqlite3.connect(DB_PATH) as conn:
        annual = pd.read_sql_query(f"""
            SELECT fiscalDateEnding, value 
            FROM {ANNUAL_TABLE}
            WHERE symbol=? AND metric='totalRevenue'
            ORDER BY fiscalDateEnding ASC
        """, conn, params=[symbol])

        quarterly = pd.read_sql_query(f"""
            SELECT fiscalDateEnding, value 
            FROM {QUARTERLY_TABLE}
            WHERE symbol=? AND metric='totalRevenue'
            ORDER BY fiscalDateEnding ASC
        """, conn, params=[symbol])

        currency = pd.read_sql_query(f"""
            SELECT reportedCurrency
            FROM {ANNUAL_TABLE}
            WHERE symbol=? AND metric='totalRevenue'
            """, conn, params=[symbol]).squeeze()
        if not currency.empty:
            currency = currency.iloc[0]

    # Cleanup
    annual["fiscalDateEnding"]   = pd.to_datetime(annual["fiscalDateEnding"], errors="coerce")
    quarterly["fiscalDateEnding"] = pd.to_datetime(quarterly["fiscalDateEnding"], errors="coerce")
    annual  = annual.dropna().rename(columns={"value": "totalRevenue"})
    quarterly = quarterly.dropna().rename(columns={"value": "totalRevenue"})
    return annual, quarterly, currency

def plot_bbg_style_revenue(symbol: str):
    annual, quarterly, currency = _load_revenue(symbol)
    if annual.empty and quarterly.empty:
        raise ValueError(f"No totalRevenue data for {symbol}")

    # Subsets (keep simple)
    a5, q5   = annual.tail(5),  quarterly.tail(20)   # ~5Y quarters
    a10, q10 = annual.tail(10), quarterly.tail(40)   # ~10Y quarters
    aall, qall = annual, quarterly

    fig = go.Figure()

    # Initial ALL view
    fig.add_bar(
        x=aall["fiscalDateEnding"], 
        y=aall["totalRevenue"],
        name="Annual Revenue",
        marker_color="#FB8B1E"  # orange accent
    )
    fig.add_bar(
        x=qall["fiscalDateEnding"], 
        y=qall["totalRevenue"],
        name="Quarterly Revenue",
        marker_color="#0068FF",  # electric blue accent
        visible="legendonly"
    )


    # Bloomberg-like layout
    fig.update_layout(
        template=BLOOMBERG_TMPL,
        barmode="group",
        title=f"{symbol} — Annual & Quaterly Values ({currency})",
    )


    fig.update_layout(
        margin=dict(l=140, r=20, t=60, b=40),  # extra left space for the legend
        legend=dict(
            orientation="v",
            x=-0.05,          # slightly outside the plotting area to the left
            xanchor="right",  # anchor the legend’s right edge to the plotting area edge
            y=1.0,
            yanchor="top"
        )
    )



    # In‑chart horizon buttons (ALL / 10Y / 5Y)
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=0.0, y=1.15,
                showactive=True,
                buttons=[
                    # ALL (keep quarterly hidden as default)
                    dict(
                        label="ALL",
                        method="update",
                        args=[
                            {
                                "x": [aall["fiscalDateEnding"], qall["fiscalDateEnding"]],
                                "y": [aall["totalRevenue"],     qall["totalRevenue"]],
                                "marker": [{"color": "#FB8B1E"}, {"color": "#0068FF"}],
                                "visible": [True, "legendonly"]  # Annual shown, Quarterly hidden
                            },
                            {"title": f"{symbol} — Total Revenue (ALL)"}
                        ],
                    ),
                    # Last 10Y (you can choose to show quarterly here)
                    dict(
                        label="Last 10Y",
                        method="update",
                        args=[
                            {
                                "x": [a10["fiscalDateEnding"], q10["fiscalDateEnding"]],
                                "y": [a10["totalRevenue"],     q10["totalRevenue"]],
                                "marker": [{"color": "#FB8B1E"}, {"color": "#0068FF"}],
                                "visible": [True, "legendonly"]  # or [True, True] if you want it visible
                            },
                            {"title": f"{symbol} — Total Revenue (10 Years)"}
                        ],
                    ),
                    # Last 5Y
                    dict(
                        label="Last 5Y",
                        method="update",
                        args=[
                            {
                                "x": [a5["fiscalDateEnding"], q5["fiscalDateEnding"]],
                                "y": [a5["totalRevenue"],     q5["totalRevenue"]],
                                "marker": [{"color": "#FB8B1E"}, {"color": "#0068FF"}],
                                "visible": [True, "legendonly"]
                            },
                            {"title": f"{symbol} — Total Revenue (5 Years)"}
                        ],
                    ),

                    # Quick toggles for Quarterly (do not change data)
                    dict(
                        label="Annual",
                        method="update",
                        args=[{"visible": [True,"legendonly"]}, {}]  # show both traces
                    ),
                    dict(
                        label="Quarterly",
                        method="update",
                        args=[{"visible": ["legendonly",True]}, {}]  # hide quarterly again
                    ),
                ]
            )
        ]
    )

    
    # For annual series
    fig.data[0].hovertemplate = "%{x|%Y}<br>Annual: %{customdata}<extra></extra>"
    fig.data[0].customdata = [human_biz(v) for v in fig.data[0].y]

    # For quarterly series
    fig.data[1].hovertemplate = "%{x|%Y-%m}<br>Quarterly: %{customdata}<extra></extra>"
    fig.data[1].customdata = [human_biz(v) for v in fig.data[1].y]
    apply_business_ticks(fig)

    fig.show()
    return fig




# ---------- CLI usage example ----------
if __name__ == "__main__":
    # Example: update for a few tickers
    tickers = ["APA"]
    #results = update_income_statements_for_list(tickers)
    #print(results)
    
    # Show it in a notebook or Python REPL
    fig = plot_bbg_style_revenue("APA")
    fig.show()

    # Save a standalone interactive HTML (shareable)
    #plot_total_revenue_interactive("APA", save_html="msft_revenue.html", auto_open=True)

