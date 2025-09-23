# modules/markets.py
"""
Markets module for RodWal Terminal.
- Keeps a persistent watchlist in config/markets.json
- Renders a formatted table (SYMBOL | LAST | CHG | CHG% | MCAP | TIME)
- Supports adding/removing tickers (e.g., 'ADD IBIT.US', 'DEL AAPL')
- Optionally fetches live data using yfinance if available; otherwise shows placeholders.

Yahoo Finance symbol tips:
- Indices: SPX -> ^GSPC, NDX -> ^NDX, DJI -> ^DJI, VIX -> ^VIX
- US Stocks: 'IBIT.US' -> 'IBIT' (we strip '.US' suffix by default)
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from typing import List, Dict, Tuple, Optional
# ---------- Paths & Storage ----------
ROOT = Path(__file__).resolve().parents[1]  # .../RodWal Terminal
CONFIG_DIR = ROOT / "config"
CONFIG_DIR.mkdir(exist_ok=True)
CONFIG_PATH = CONFIG_DIR / "markets.json"

# Default watchlist: you can edit this list or override via config/markets.json
DEFAULT_WATCHLIST = ["SPX", "NDX", "DJI", "VIX", "BTC-USD", "GC=F"]

# Map friendly codes -> Yahoo Finance tickers
ALIASES = {
    "SPX": "^GSPC",
    "NDX": "^NDX",
    "DJI": "^DJI",
    "VIX": "^VIX",
}

# ---------- Helpers ----------
def _now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")

def load_watchlist() -> List[str]:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("tickers"), list):
                return data["tickers"]
        except Exception:
            pass
    return DEFAULT_WATCHLIST.copy()

def save_watchlist(tickers: List[str]) -> None:
    data = {"tickers": tickers}
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def normalize_ticker(symbol: str) -> str:
    """
    Normalize user input (e.g., ' ibit.us  ' -> 'IBIT').
    - Strip whitespace, use uppercase
    - Strip trailing '.US' suffix commonly used by some platforms
    - Keep dots for genuine symbols like 'BRK.B'
    """
    s = (symbol or "").strip().upper()
    if s.endswith(".US"):
        s = s[:-3]
    return s

def to_yahoo_symbol(symbol: str) -> str:
    """
    Convert friendly symbol to Yahoo Finance symbol if needed.
    """
    base = normalize_ticker(symbol)
    return ALIASES.get(base, base)

# ---------- Data Fetch ----------
def _try_import_yf():
    try:
        import yfinance as yf  # type: ignore
        return yf
    except Exception:
        return None

def _to_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

@dataclass
class Quote:
    symbol: str      # display symbol (friendly, e.g., SPX or IBIT)
    ysym: str        # yahoo symbol (e.g., ^GSPC)
    last: Optional[float]
    chg: Optional[float]
    chg_pct: Optional[float]
    mcap: Optional[float]     # <--- Market cap in absolute dollars
    time_str: str

def fetch_quotes(tickers: List[str]) -> List[Quote]:
    """
    Fetch quotes for a list of tickers. If yfinance is available, use it.
    Otherwise, return records with None for numeric fields (rendered as '--').
    """
    yf = _try_import_yf()
    results: List[Quote] = []
    now_str = _now_hhmm()
    seen = set()

    for sym in tickers:
        disp = normalize_ticker(sym)
        ysym = to_yahoo_symbol(sym)

        if disp in seen:
            continue
        seen.add(disp)

        last = chg = chg_pct = None
        mcap = None

        if yf:
            try:
                t = yf.Ticker(ysym)
                # --- Try fast_info first (fast + low overhead) ---
                fi = getattr(t, "fast_info", None)
                if fi:
                    last = _to_float(fi.get("last_price") or fi.get("lastPrice"))
                    prev = _to_float(fi.get("previous_close") or fi.get("previousClose"))
                    # Some instruments (indices, futures) don't have MCAP
                    mcap = _to_float(fi.get("market_cap") or fi.get("marketCap"))

                    if last is not None and prev:
                        chg = last - prev
                        chg_pct = (chg / prev) * 100.0

                # --- Fallbacks if needed ---
                if last is None:
                    hist = t.history(period="2d", interval="1d")
                    if not hist.empty:
                        last = float(hist["Close"].iloc[-1])
                        if len(hist) > 1:
                            prev = float(hist["Close"].iloc[-2])
                            chg = last - prev
                            chg_pct = (chg / prev) * 100.0 if prev else None

                if mcap is None:
                    # Slower, but more complete; may be unavailable for indices/futures
                    info = {}
                    try:
                        info = t.info or {}
                    except Exception:
                        info = {}
                    mcap = _to_float(info.get("marketCap"))

            except Exception:
                # Swallow and leave fields as None (rendered as "--")
                pass

        results.append(Quote(
            symbol=disp,
            ysym=ysym,
            last=last,
            chg=chg,
            chg_pct=chg_pct,
            mcap=mcap,
            time_str=now_str,
        ))

    return results

# ---------- Watchlist Ops ----------
def add_ticker(symbol: str) -> Tuple[bool, str]:
    """
    Add a symbol to the watchlist. Returns (added?, message)
    """
    wl = load_watchlist()
    sym = normalize_ticker(symbol)
    if not sym:
        return False, "Ticker cannot be empty."
    if sym in wl:
        return False, f"{sym} is already on the list."
    wl.append(sym)
    save_watchlist(wl)
    return True, f"Added {sym}."

def remove_ticker(symbol: str) -> Tuple[bool, str]:
    wl = load_watchlist()
    sym = normalize_ticker(symbol)
    if sym not in wl:
        return False, f"{sym} not found."
    wl = [s for s in wl if s != sym]
    save_watchlist(wl)
    return True, f"Removed {sym}."

def list_tickers() -> List[str]:
    return load_watchlist()

# ---------- Rendering ----------
def _view_header(title: str) -> str:
    banner = f"=== {title} ==="
    line = "-" * len(banner)
    return f"{banner}\n{line}\n"

def _fmt_val(x: Optional[float], width: int, prec: int = 2) -> str:
    if x is None:
        return "--".rjust(width)
    s = f"{x:,.{prec}f}"
    return s.rjust(width)

def _fmt_signed(x: Optional[float], width: int, prec: int = 2) -> str:
    if x is None:
        return "--".rjust(width)
    sign = "+" if x >= 0 else ""
    s = f"{sign}{x:,.{prec}f}"
    return s.rjust(width)

def _fmt_mcap(x: Optional[float], width: int) -> str:
    """
    Format market cap to K/M/B/T with 1–2 decimals.
    Examples: 2.1T, 415.6B, 12.3M
    """
    if x is None or x <= 0:
        return "--".rjust(width)
    absx = abs(x)
    if absx >= 1_000_000_000_000:
        s = f"{x / 1_000_000_000_000:.2f}T"
    elif absx >= 1_000_000_000:
        s = f"{x / 1_000_000_000:.2f}B"
    elif absx >= 1_000_000:
        s = f"{x / 1_000_000:.2f}M"
    elif absx >= 1_000:
        s = f"{x / 1_000:.2f}K"
    else:
        s = f"{x:.0f}"
    return s.rjust(width)

def render_markets() -> str:
    """
    Returns a string table for the current watchlist, including Market Cap.
    """
    wl = load_watchlist()
    quotes = fetch_quotes(wl)

    # column widths (tweak as needed)
    w_sym, w_last, w_chg, w_chg_pct, w_mcap, w_time = 10, 10, 10, 8, 10, 6

    lines = []
    lines.append(_view_header("Market Quotes Monitor (MKT)"))
    lines.append(
        f"{'SYMBOL'.ljust(w_sym)}"
        f"{'LAST'.rjust(w_last)}"
        f"{'CHG'.rjust(w_chg)}"
        f"{'CHG%'.rjust(w_chg_pct)}"
        f"{'MCAP'.rjust(w_mcap)}"
        f"{'TIME'.rjust(w_time)}"
    )
    lines.append("-" * (w_sym + w_last + w_chg + w_chg_pct + w_mcap + w_time))

    for q in quotes:
        last_s = _fmt_val(q.last, w_last)
        chg_s  = _fmt_signed(q.chg, w_chg)
        pct_s  = _fmt_signed(q.chg_pct, w_chg_pct, prec=2) if q.chg_pct is not None else "--".rjust(w_chg_pct)
        mcap_s = _fmt_mcap(q.mcap, w_mcap)
        time_s = q.time_str.rjust(w_time)
        lines.append(f"{q.symbol.ljust(w_sym)}{last_s}{chg_s}{pct_s}{mcap_s}{time_s}")

    lines.append("\nCommands: ADD <ticker> | DEL <ticker> | LIST")
    lines.append("Tip: You can enter 'IBIT.US' and we'll normalize it to 'IBIT'.")
    return "\n".join(lines)
