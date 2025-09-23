# modules/charts.py
"""
Graphs module for RodWal Terminal
- Bar charts (Yearly / Quarterly / Monthly) for:
  * Market Cap (MCAP)
  * Revenue (Total Revenue)
  * Earnings (Net Income)
  * FCF (Free Cash Flow = CFO - CapEx, if FCF not explicit)
- Uses yfinance; falls back gracefully if not installed.
- Opens a Tk Toplevel with a Matplotlib canvas (no terminal flicker).
"""

from __future__ import annotations
import math
from datetime import datetime
from functools import lru_cache
from typing import Optional, Tuple
from core.theme import *

# Matplotlib (TkAgg backend used implicitly by FigureCanvasTkAgg)
import matplotlib
matplotlib.use("TkAgg")  # ensure Tk backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter

# Try to reuse normalization helpers
try:
    from module.markets import normalize_ticker, to_yahoo_symbol
except Exception:
    def normalize_ticker(s: str) -> str:
        s = (s or "").strip().upper()
        if s.endswith(".US"): s = s[:-3]
        return s
    def to_yahoo_symbol(s: str) -> str:
        return normalize_ticker(s)

# ---------- yfinance loader ----------
def _try_import_yf():
    try:
        import yfinance as yf
        return yf
    except Exception:
        return None

# ---------- Human formatting ----------
def _fmt_billions(x, pos=None):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return ""
    ax = abs(x)
    if ax >= 1_000_000_000_000:
        return f"{x/1_000_000_000_000:.1f}T"
    if ax >= 1_000_000_000:
        return f"{x/1_000_000_000:.1f}B"
    if ax >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    return f"{x:,.0f}"

def _safe_series(df, key):
    try:
        return df.loc[key]
    except Exception:
        return None

# ---------- Data: Market Cap ----------
# --- REPLACE your _shares_series and _historical_mcap with this ---

from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=64)
def _shares_series(yf, ysym: str):
    """
    Return a (DatetimeIndex -> float) Series with shares outstanding.
    Priority:
      1) get_shares_full() normalized to a single numeric series
      2) fast_info.shares_outstanding as a constant series
      3) fallback: derive constant shares ~ market_cap / last_price (approx)
    """
    import pandas as pd
    t = yf.Ticker(ysym)

    # 1) Try historical shares (preferred)
    try:
        df = t.get_shares_full(start="1990-01-01")
        if df is not None and not df.empty:
            # Normalize to a single numeric column
            if isinstance(df, pd.DataFrame):
                # prefer a column named like 'Shares Outstanding', else first numeric column
                cand = None
                for col in df.columns:
                    if "share" in str(col).lower():
                        cand = col
                        break
                if cand is None:
                    # pick first numeric column
                    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                    cand = num_cols[0] if num_cols else df.columns[0]
                s = df[cand]
            else:
                s = df.squeeze()

            s = pd.to_numeric(s, errors="coerce")  # ensure numeric
            s = s.dropna()
            if not s.empty:
                s.index = pd.to_datetime(s.index).tz_localize(None)
                # Make sure shares are positive
                s = s[s > 0]
                if not s.empty:
                    return s.sort_index()
    except Exception:
        pass

    # 2) Fast info constant shares
    try:
        fi = {}
        try:
            fi = t.fast_info or {}
        except Exception:
            fi = {}
        shares = fi.get("shares_outstanding") or fi.get("sharesOutstanding")
        if shares and float(shares) > 0:
            # build a constant monthly series from 1990 to now
            idx = pd.date_range("1990-01-31", datetime.now().date(), freq="M")
            return pd.Series([float(shares)] * len(idx), index=idx)
    except Exception:
        pass

    # 3) Last-resort approximation: market cap / last price -> constant shares
    try:
        fi = {}
        try:
            fi = t.fast_info or {}
        except Exception:
            fi = {}
        mcap = fi.get("market_cap") or fi.get("marketCap")
        last = fi.get("last_price") or fi.get("lastPrice")
        if (mcap and last) and float(last) != 0:
            approx_shares = float(mcap) / float(last)
            if approx_shares > 0:
                idx = pd.date_range("1990-01-31", datetime.now().date(), freq="M")
                return pd.Series([approx_shares] * len(idx), index=idx)
    except Exception:
        pass

    return None


def _historical_mcap(yf, ysym: str, freq: str):
    """
    Compute historical Market Cap = Price * Shares Outstanding
    freq ∈ {"Y","Q","M"}  (Yearly, Quarterly, Monthly)
    - Uses monthly price history for efficiency, resampled for Y/Q.
    - Accepts both 'Adj Close' and 'Close' depending on yfinance version/flags.
    - Aligns and forward-fills shares to avoid NaNs.
    """
    import pandas as pd
    t = yf.Ticker(ysym)

    try:
        # Pull monthly prices; auto_adjust=True ensures 'Close' is adjusted
        px = t.history(period="max", interval="1mo", auto_adjust=True)
        if px is None or px.empty:
            return None

        # Be tolerant of column names: prefer 'Adj Close', else 'Close'
        price_col = "Adj Close" if "Adj Close" in px.columns else ("Close" if "Close" in px.columns else None)
        if price_col is None:
            return None

        px = px[[price_col]].rename(columns={price_col: "Price"})
        px.index = pd.to_datetime(px.index).tz_localize(None)

        shares = _shares_series(yf, ysym)
        if shares is None or shares.empty:
            return None

        # Align monthly index; forward-fill shares
        s = shares.copy()
        s.index = pd.to_datetime(s.index).tz_localize(None)

        # Join and compute MCAP
        df = px.join(s.rename("Shares"), how="left")
        df["Shares"] = df["Shares"].ffill()
        # guard against any zeros or NaN
        df = df.dropna(subset=["Price", "Shares"])
        df = df[df["Shares"] > 0]

        df["MCAP"] = df["Price"].astype(float) * df["Shares"].astype(float)

        if df["MCAP"].empty:
            return None

        if freq == "M":
            out = df["MCAP"]
        elif freq == "Q":
            out = df["MCAP"].resample("Q").last()
        else:
            out = df["MCAP"].resample("Y").last()

        out = out.dropna()
        # Some tickers produce extremely large dtype -> cast to float64
        out = out.astype("float64")

        # sanity: remove negatives (shouldn’t happen but just in case)
        out = out[out >= 0]

        return out
    except Exception:
        return None

# ---------- Data: Financial metrics (Revenue, Earnings, FCF) ----------
def _financial_series(yf, ysym: str, metric: str, freq: str):
    """
    metric in {"REVENUE","EARNINGS","FCF"}; freq in {"Y","Q","M"}
    Y -> annual financials
    Q -> quarterly financials
    M -> monthly TTM (rolling sum of last 4 quarters) forward-filled to month end
    """
    import pandas as pd
    t = yf.Ticker(ysym)
    metric = metric.upper()

    # Pull annual & quarterly statements
    try:
        fin_a = t.financials if hasattr(t, "financials") else None  # annual income stmt
    except Exception:
        fin_a = None
    try:
        fin_q = t.quarterly_financials if hasattr(t, "quarterly_financials") else None
    except Exception:
        fin_q = None
    try:
        cf_a = t.cashflow if hasattr(t, "cashflow") else None
    except Exception:
        cf_a = None
    try:
        cf_q = t.quarterly_cashflow if hasattr(t, "quarterly_cashflow") else None
    except Exception:
        cf_q = None

    # helper to compute FCF row if missing
    def build_fcf(cf_df):
        if cf_df is None or cf_df.empty:
            return None
        # Some tickers expose "Free Cash Flow" directly; else CFO - CapEx
        fcf = _safe_series(cf_df, "Free Cash Flow")
        if fcf is not None:
            return fcf
        cfo = _safe_series(cf_df, "Total Cash From Operating Activities")
        capex = _safe_series(cf_df, "Capital Expenditures")  # usually negative
        if cfo is None or capex is None:
            return None
        return (cfo + capex)

    # choose row according to metric
    def pick_row(fin_df, cf_df):
        if fin_df is None and cf_df is None:
            return None
        if metric == "REVENUE":
            return _safe_series(fin_df, "Total Revenue") if fin_df is not None else None
        if metric == "EARNINGS":
            # interpret "earnings" as Net Income
            return _safe_series(fin_df, "Net Income") if fin_df is not None else None
        if metric == "FCF":
            return build_fcf(cf_df)
        return None

    if freq in ("Y", "Q"):
        df = pick_row(fin_a if freq == "Y" else fin_q, cf_a if freq == "Y" else cf_q)
        if df is None or df.empty:
            return None
        # yfinance returns columns as dates; transpose to Series(date->value)
        ser = df.T.squeeze()
        ser.index = pd.to_datetime(ser.index).tz_localize(None)
        ser = ser.sort_index()
        return ser

    # Monthly: compute TTM from quarterly, then ffill to months
    if freq == "M":
        q = pick_row(fin_q, cf_q)
        if q is None or q.empty:
            return None
        q = q.T.squeeze().sort_index()
        q.index = pd.to_datetime(q.index).tz_localize(None)
        # TTM = rolling sum of last 4 quarters
        ttm = q.rolling(4).sum().dropna()
        # forward-fill to month-end
        idx = pd.date_range(ttm.index.min().to_period("M").to_timestamp("M"),
                            datetime.now(), freq="M")
        ttm_monthly = ttm.reindex(idx, method="ffill")
        return ttm_monthly

    return None

# ---------- Charting ----------
def _make_bars(fig, ax, series, title, ylabel, color=ACCENT_AMBER):
    ax.bar(series.index, series.values, color=color, width=80 if len(series) < 20 else 120)
    ax.set_title(title, loc="left", fontsize=12, pad=12, color=FG_TEXT)
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_billions))
    ax.grid(axis="y", alpha=0.25)
    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_ha("right")
        label.set_color(FG_TEXT)
    for label in ax.get_yticklabels():
        label.set_color(FG_TEXT)
    ax.set_ylabel(ylabel, color = FG_TEXT)

def _normalize_inputs(symbol: str, metric: str, freq: str) -> Tuple[str, str, str]:
    disp = normalize_ticker(symbol)
    freq = (freq or "Y").upper()
    metric = (metric or "MCAP").upper()
    if freq not in ("Y", "Q", "M"):
        freq = "Y"
    if metric not in ("MCAP", "REVENUE", "EARNINGS", "FCF"):
        metric = "MCAP"
    return disp, metric, freq

def _title_for(disp: str, metric: str, freq: str):
    period = {"Y": "Yearly", "Q": "Quarterly", "M": "Monthly TTM"}.get(freq, "Yearly")
    pretty = {"MCAP":"Market Cap", "REVENUE":"Revenue", "EARNINGS":"Net Income", "FCF":"Free Cash Flow"}.get(metric, metric)
    return f"{disp} — {pretty} ({period})"

def _color_for(metric: str) -> str:
    return {"MCAP": ACCENT_AMBER, "REVENUE": ACCENT_AMBER, "EARNINGS": ACCENT_GREEN, "FCF":ACCENT_GREEN}.get(metric, "#56b0ff")

def _ylabel_for(metric: str) -> str:
    return "USD"

def open_chart_window(root, symbol: str, metric: str = "MCAP", freq: str = "Y"):
    """
    Create a Tk Toplevel window with the requested bar chart.
    """
    import tkinter as tk
    from tkinter import messagebox

    disp, metric, freq = _normalize_inputs(symbol, metric, freq)
    ysym = to_yahoo_symbol(disp)
    yf = _try_import_yf()
    if not yf:
        messagebox.showerror("Graphs", "yfinance is not installed. Please install yfinance to enable charts.")
        return

    # Pull data
    if metric == "MCAP":
        ser = _historical_mcap(yf, ysym, freq)
    else:
        ser = _financial_series(yf, ysym, metric, freq)

    if ser is None or len(ser) == 0:
        messagebox.showwarning("Graphs", f"No data available for {disp} · {metric} ({freq}).")
        return

    # Optional: trim to a reasonable count (avoid overcrowded bars)
    max_points = 36 if freq == "M" else (24 if freq == "Q" else 20)
    if len(ser) > max_points:
        ser = ser.iloc[-max_points:]

    # Build window
    win = tk.Toplevel(root)
    win.title(f"Chart · {disp} · {metric} ({freq})")
    win.configure(bg="#0f1116")
    win.geometry("900x520")

    fig, ax = plt.subplots(figsize=(9.0, 4.8), dpi=100)
    fig.patch.set_facecolor("#0f1116")
    ax.set_facecolor("#0f1116")
    _make_bars(fig, ax, ser, _title_for(disp, metric, freq), _ylabel_for(metric), _color_for(metric))
    plt.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    # Close hook to release figure memory
    def _on_close():
        try:
            plt.close(fig)
        except Exception:
            pass
        win.destroy()
    win.protocol("WM_DELETE_WINDOW", _on_close)

def view_charts_help() -> str:
    lines = [
        "=== Charts (GFX) ===",
        "View bar charts for Market Cap, Revenue, Net Income, and FCF.",
        "",
        "Usage:",
        "  CHART <ticker> [metric] [freq]",
        "    metric ∈ {MCAP, REVENUE, EARNINGS, FCF} (default: MCAP)",
        "    freq   ∈ {Y, Q, M}  -> Yearly, Quarterly, Monthly (TTM for fundamentals)",
        "",
        "Examples:",
        "  CHART AAPL                    # yearly market cap",
        "  CHART MSFT REVENUE Y          # yearly revenue",
        "  CHART NVDA EARNINGS Q         # quarterly net income",
        "  CHART AMZN FCF M              # monthly TTM free cash flow",
        "",
        "Notes:",
        "  • Market Cap uses Adj Close × Shares Outstanding (historical where available).",
        "  • Monthly fundamentals use TTM (rolling sum of last 4 quarters), forward-filled to month end.",
        "  • Data source: Yahoo Finance (delayed). Availability varies by instrument.",
    ]
    return "\n".join(lines)
