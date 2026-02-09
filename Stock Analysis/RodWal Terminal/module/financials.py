
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


# ---------- Graphs ----------

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

ANNUAL_COLOR = "#FB8B1E"   # orange accent
QUARTERLY_COLOR = "#E9A25A"  # electric blue accent

def _load_revenue(symbol: str):
    with sqlite3.connect(DB_PATH) as conn:
        annual = pd.read_sql_query(
            f"""
            SELECT fiscalDateEnding, value 
            FROM {ANNUAL_TABLE}
            WHERE symbol=? AND metric='totalRevenue'
            ORDER BY fiscalDateEnding ASC
            """,
            conn, params=[symbol]
        )

        quarterly = pd.read_sql_query(
            f"""
            SELECT fiscalDateEnding, value 
            FROM {QUARTERLY_TABLE}
            WHERE symbol=? AND metric='totalRevenue'
            ORDER BY fiscalDateEnding ASC
            """,
            conn, params=[symbol]
        )

        currency = pd.read_sql_query(
            f"""
            SELECT reportedCurrency
            FROM {ANNUAL_TABLE}
            WHERE symbol=? AND metric='totalRevenue'
            """,
            conn, params=[symbol]
        ).squeeze()
        if not currency.empty:
            currency = currency.iloc[0]
        else:
            currency = ""

    # Cleanup
    annual["fiscalDateEnding"]    = pd.to_datetime(annual["fiscalDateEnding"], errors="coerce")
    quarterly["fiscalDateEnding"] = pd.to_datetime(quarterly["fiscalDateEnding"], errors="coerce")
    annual    = annual.dropna().rename(columns={"value": "totalRevenue"})
    quarterly = quarterly.dropna().rename(columns={"value": "totalRevenue"})
    return annual, quarterly, currency


def plot_bbg_style_revenue(symbol: str):
    annual, quarterly, currency = _load_revenue(symbol)
    if annual.empty and quarterly.empty:
        raise ValueError(f"No totalRevenue data for {symbol}")

    # Subsets
    a5, q5     = annual.tail(5),   quarterly.tail(20)   # ~5Y quarters
    a10, q10   = annual.tail(10),  quarterly.tail(40)   # ~10Y quarters
    aall, qall = annual, quarterly

    fig = go.Figure()

    # Initial ALL view
    fig.add_bar(
        x=aall["fiscalDateEnding"],
        y=aall["totalRevenue"],
        name="Annual Revenue",
        marker_color=ANNUAL_COLOR
    )
    fig.add_bar(
        x=qall["fiscalDateEnding"],
        y=qall["totalRevenue"],
        name="Quarterly Revenue",
        marker_color=QUARTERLY_COLOR,
        visible="legendonly"  # hidden by default
    )

    # Bloomberg-like base layout
    fig.update_layout(
        template=BLOOMBERG_TMPL,
        barmode="group",
        title=dict(
            text=f"{symbol} — Annual & Quarterly Values ({currency})",
            x=0.5, xanchor="center",
        ),
        # Reserve space on top for two rows of buttons + labels
        margin=dict(l=60, r=20, t=120, b=50),
        # Legend: horizontal near top (keeps top area clean yet visible)
        legend=dict(
            orientation="h",
            yanchor="bottom", y=0.99,
            xanchor="left",   x=0.0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11)
        ),
        # Hover styling that fits dark Bloomberg feel (template usually handles most)
        hoverlabel=dict(
            bgcolor="#1C1F25",
            font_size=12,
            font_color="#E6E6E6"
        ),
        # Gentle transitions on updates
        transition=dict(duration=250, easing="cubic-in-out"),
        # Axes: subtle gridlines for dark background
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=11)),
        yaxis=dict(gridcolor="#23272E", zeroline=False, tickfont=dict(size=11)),
    )

    # Two rows of centered, pill-styled buttons
    fig.update_layout(
        updatemenus=[
            # Row 1: Horizon buttons
            dict(
                type="buttons",
                direction="right",
                x=0, y=1.15,
                xanchor="center", yanchor="top",
                showactive=True,
                active=0,  # default: ALL
                bgcolor="#1C1F25",
                bordercolor="#2A2F36",
                borderwidth=1,
                pad=dict(r=4, l=4, t=4, b=4),
                buttons=[
                    # ALL (Quarterly hidden)
                    dict(
                        label="ALL",
                        method="update",
                        args=[
                            {
                                "x": [aall["fiscalDateEnding"], qall["fiscalDateEnding"]],
                                "y": [aall["totalRevenue"],     qall["totalRevenue"]],
                                "marker": [{"color": ANNUAL_COLOR}, {"color": QUARTERLY_COLOR}],
                                "visible": [True, "legendonly"],
                            },
                            {"title": f"{symbol} — Total Revenue (ALL)"}
                        ],
                    ),
                    # Last 10Y
                    dict(
                        label="Last 10Y",
                        method="update",
                        args=[
                            {
                                "x": [a10["fiscalDateEnding"], q10["fiscalDateEnding"]],
                                "y": [a10["totalRevenue"],     q10["totalRevenue"]],
                                "marker": [{"color": ANNUAL_COLOR}, {"color": QUARTERLY_COLOR}],
                                "visible": [True, "legendonly"],
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
                                "marker": [{"color": ANNUAL_COLOR}, {"color": QUARTERLY_COLOR}],
                                "visible": [True, "legendonly"],
                            },
                            {"title": f"{symbol} — Total Revenue (5 Years)"}
                        ],
                    ),
                ],
            ),
            # Row 2: Frequency buttons
            dict(
                type="buttons",
                direction="right",
                x=0.2, y=1.15,
                xanchor="center", yanchor="top",
                showactive=True,
                active=0,  # default: Annual
                bgcolor="#1C1F25",
                bordercolor="#2A2F36",
                borderwidth=1,
                pad=dict(r=4, l=4, t=4, b=4),
                buttons=[
                    dict(
                        label="Annual",
                        method="update",
                        args=[{"visible": [True, "legendonly"]}, {}]
                    ),
                    dict(
                        label="Quarterly",
                        method="update",
                        args=[{"visible": ["legendonly", True]}, {}]
                    ),
                ],
            ),
        ]
    )

    # Group labels above menus (annotation)
    fig.add_annotation(
        x=-0.01, y=1.19, xref="paper", yref="paper",
        text="Horizon", showarrow=False,
        font=dict(size=12, color="#AEB4BC")
    )
    fig.add_annotation(
        x=0.175, y=1.19, xref="paper", yref="paper",
        text="Frequency", showarrow=False,
        font=dict(size=12, color="#AEB4BC")
    )

    # Hover templates and humanized values
    fig.data[0].hovertemplate = "%{x|%Y}<br>Annual: %{customdata}<extra></extra>"
    fig.data[0].customdata = [human_biz(v) for v in fig.data[0].y]

    fig.data[1].hovertemplate = "%{x|%Y-%m}<br>Quarterly: %{customdata}<extra></extra>"
    fig.data[1].customdata = [human_biz(v) for v in fig.data[1].y]

    # Business ticks from your style module
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

