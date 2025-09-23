import tkinter as tk
from tkinter import ttk
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Internal Modules and Blueprints
from core.theme import *
from module import markets, charts  # Imports Markets Module - It fetches last data on indices


# ---------- Views ----------
def view_header(title: str) -> str:
    banner = f"=== {title} ==="
    line = "-" * len(banner)
    return f"{banner}\n{line}\n"


def view_markets():
    """
    Wrap the markets text with a header and a clear delayed-source banner.
    The actual fetching is handled asynchronously by TerminalApp.load_view_async.
    """
    header = view_header("Markets")
    delayed = "Source: Yahoo Finance — Delayed feed (~15m)\n\n"
    return header + delayed + markets.render_markets()


def view_help():
    body = [
        view_header("Help"),
        "Welcome to RodWal Terminal.\n",
        "Commands:",
        "  MKT        -> Markets monitor",
        "  ADD <sym>  -> Add symbol to watchlist (e.g., ADD AAPL)",
        "  DEL <sym>  -> Remove symbol from watchlist (e.g., DEL AAPL)",
        "  LIST       -> Show current watchlist",
        "",
        "Tips:",
        " - Markets data is fetched asynchronously to keep the UI responsive.",
        " - Feed: Yahoo Finance — Delayed (~15 minutes) depending on the instrument.",
        " - Use the buttons or the command bar to navigate.",
        "",
    ]
    return "\n".join(body)


def view_stub(name: str):
    return view_header(name) + "Coming soon...\n"


# --- Router for commands -> views ---
VIEWS = {
    "MKT": view_markets,
    "GFX": charts.view_charts_help, # Charts Help
    "HELP": view_help,
    "N": lambda: view_stub("News"),
    "FX": lambda: view_stub("FX Dashboard"),
    "FICC": lambda: view_stub("Fixed Income & Commodities"),
    "CMDY": lambda: view_stub("Commodities"),
    "EQS": lambda: view_stub("Equity Screener"),
    "ECO": lambda: view_stub("Economic Calendar"),
    "PORT": lambda: view_stub("Portfolio View"),
    "SET": lambda: view_stub("Settings"),
}


# --- Simple tooltip helper ---
class ToolTip:
    def __init__(self, widget, text: str, delay_ms=400):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.delay_ms = delay_ms
        self._after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)

    def _schedule(self, _event=None):
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _show(self):
        if self.tipwindow or not self.text:
            return
        if self.widget == self.widget.focus_get():
            bbox = self.widget.bbox("insert")
            x, y, cx, cy = bbox if bbox else (0, 0, 0, 0)
        else:
            x, y, cx, cy = (0, 0, 0, 0)

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.configure(bg="#222")
        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#222", foreground="#fff",
            relief=tk.SOLID, borderwidth=1,
            font=("Segoe UI", 9)
        )
        label.pack(ipadx=8, ipady=4)

        # Position the tooltip
        tw.wm_geometry(f"+{x}+{y}")

    def _hide(self, _event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        tw = self.tipwindow
        if tw:
            tw.destroy()
        self.tipwindow = None


class TerminalApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RodWal Terminal")
        self.root.geometry("1200x820")
        self.root.configure(bg=BG_DARK)

        # Thread pool for background tasks
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._spinner_job = None
        self._pending_tasks = {}  # track per-view task to ignore stale results

        # macOS: better looking titlebar when supported
        try:
            self.root.tk.call('tk', 'scaling', 1.2)
        except Exception:
            pass

        self._build_ui()
        self._bind_keys()
        self._tick_clock()

        # Proper cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Show initial help screen
        self.load_view("HELP")

    # ---- UI ----
    def _build_ui(self):
        # Top Header
        header = tk.Frame(self.root, bg=BG_PANEL)
        header.pack(side=tk.TOP, fill=tk.X)

        title = tk.Label(
            header, text="●  RodWal Capital Strategies — Terminal",
            bg=BG_PANEL, fg=ACCENT_GREEN, font=FONT_TITLE
        )
        title.pack(side=tk.LEFT, padx=12, pady=10)

        self.time_label = tk.Label(
            header, text="--:--:--", bg=BG_PANEL, fg=FG_MUTED, font=FONT_LABEL
        )
        self.time_label.pack(side=tk.RIGHT, padx=12)

        # Buttons Panel
        buttons_panel = tk.Frame(self.root, bg=BG_DARK)
        buttons_panel.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(8, 4))

        btns = [
            ("MKT", "Markets", ACCENT_AMBER, "Market Monitor"),
            ("GFX", "GFX", ACCENT_BLUE, "Charts / Graphs"),
            ("N",   "News",    ACCENT_BLUE,   "Top News"),
            ("FX",  "FX",      ACCENT_AMBER, "FX Dashboard"),
            ("FICC","FICC",    ACCENT_PURPLE, "Fixed Income & Commodities"),
            ("CMDY","CMDY",    ACCENT_PURPLE, "Commodities"),
            ("EQS", "EQS",     ACCENT_AMBER, "Equity Screener"),
            ("ECO", "ECO",     ACCENT_AMBER, "Economic Calendar"),
            ("PORT","PORT",    ACCENT_GREEN,  "Portfolio View"),
            ("SET", "SET",     ACCENT_BLUE,   "Settings"),
            ("HELP","HELP",    ACCENT_GREEN,  "Help"),
            ("QUIT","QUIT",    ACCENT_RED,    "Exit Application"),
        ]

        for code, label, color, tip in btns:
            if code == "QUIT":
                cmd = self._on_close
            else:
                cmd = (lambda c=code: self.load_view(c))
            b = tk.Button(
                buttons_panel, text=f"{label}",
                command=cmd,
                bg=color, fg="black", activebackground=color, activeforeground="black",
                relief=tk.FLAT, font=FONT_BUTTON, padx=14, pady=6, cursor="hand2"
            )
            b.pack(side=tk.LEFT, padx=6, pady=4)
            ToolTip(b, f"{tip}  ·  Mnemonic: {code}")

        # Command Bar
        cmd_bar = tk.Frame(self.root, bg=BG_DARK)
        cmd_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(6, 8))

        lbl = tk.Label(cmd_bar, text="Command:", bg=BG_DARK, fg=FG_MUTED, font=FONT_LABEL)
        lbl.pack(side=tk.LEFT)

        self.cmd_entry = tk.Entry(
            cmd_bar, bg="#1a1c22", fg=FG_TEXT, insertbackground=FG_TEXT,
            width=20, font=FONT_LABEL, relief=tk.FLAT
        )
        self.cmd_entry.pack(side=tk.LEFT, padx=8)
        self.cmd_entry.bind("<Return>", self._on_enter)

        hint = tk.Label(
            cmd_bar,
            text="Try: MKT, N, FX, FICC, CMDY, EQS, ECO, PORT, HELP, SET",
            bg=BG_DARK, fg=FG_MUTED, font=("Segoe UI", 9)
        )
        hint.pack(side=tk.LEFT, padx=10)

        # Content Panel
        content_frame = tk.Frame(self.root, bg=BG_DARK)
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        # Text area with scrollbar
        self.text = tk.Text(
            content_frame, wrap=tk.NONE, bg="#0f1116", fg=FG_TEXT, insertbackground=FG_TEXT,
            relief=tk.FLAT, font=FONT_MONO, undo=False
        )
        yscroll = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.text.yview)
        xscroll = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=self.text.xview)
        self.text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # Status Bar
        status = tk.Frame(self.root, bg=BG_PANEL)
        status.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_left = tk.Label(
            status,
            text="Connected — Yahoo Finance (Delayed ⧗ ~15m)",
            bg=BG_PANEL, fg=ACCENT_GREEN, font=FONT_LABEL
        )
        self.status_left.pack(side=tk.LEFT, padx=12, pady=6)

        self.status_right = tk.Label(status, text="Ready", bg=BG_PANEL, fg=FG_MUTED, font=FONT_LABEL)
        self.status_right.pack(side=tk.RIGHT, padx=12)

    # ---- Key bindings & clock ----
    def _bind_keys(self):
        self.root.bind("<Escape>", lambda e: self.clear())
        self.root.bind("<F1>", lambda e: self.load_view("HELP"))
        self.root.bind("<Control-q>", lambda e: self._on_close())

    def _tick_clock(self):
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.time_label.configure(text=now)
        self.root.after(1000, self._tick_clock)

    # ---- Spinner helpers (status_right) ----
    def _start_spinner(self, prefix="Loading…"):
        frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        state = {"i": 0}

        def tick():
            self.status_right.configure(text=f"{prefix} {frames[state['i']]}")
            state["i"] = (state["i"] + 1) % len(frames)
            self._spinner_job = self.root.after(80, tick)

        self._stop_spinner(None)
        tick()

    def _stop_spinner(self, final_text: str | None):
        if self._spinner_job:
            self.root.after_cancel(self._spinner_job)
            self._spinner_job = None
        if final_text is not None:
            self.status_right.configure(text=final_text)

    def _loading_screen(self, code: str) -> str:
        return (
            view_header(f"{code} — Loading")
            + "Source: Yahoo Finance — Delayed feed (~15m)\n\n"
            + "Please wait while we fetch the latest snapshot...\n"
        )

    # ---- Async view loader ----
    # Terminal.py  (inside class TerminalApp)
    # CHANGE 1/3: add show_loading flag (default True for first loads)
    def load_view_async(self, code: str, fn, *args, refresh_ms=None, show_loading: bool = True):
        # Only show full-screen loading banner when explicitly asked
        if show_loading:
            self.set_text(self._loading_screen(code))  # full-screen banner only on first load

        self._start_spinner(prefix=f"Loading {code}…")

        prev = self._pending_tasks.get(code)
        if prev is not None and not prev.done():
            self._pending_tasks[code] = None

        future = self.executor.submit(fn, *args)
        self._pending_tasks[code] = future

        def on_done(fut):
            def ui_update():
                if self._pending_tasks.get(code) is not fut:
                    return
                try:
                    content = fut.result()
                    # Optional: only update if changed (reduces redraw)
                    current = self.text.get("1.0", "end-1c")
                    if content != current:
                        self.set_text(content)
                    self._stop_spinner(f"Loaded: {code}")
                except Exception as e:
                    self._stop_spinner(f"Error loading {code}")
                    # Keep current table; just append the error
                    self.append_text(f"\n[Error] {e}\n")

                # ---------- keep it live without wiping the table ----------
                if refresh_ms:
                    self.root.after(
                        refresh_ms,
                        lambda: self.load_view_async(code, fn, *args, refresh_ms=refresh_ms, show_loading=False)
                    )
                # -----------------------------------------------------------

            self.root.after(0, ui_update)

        future.add_done_callback(on_done)


    # ---- Actions ----
    def _on_enter(self, _event=None):
        code = self.cmd_entry.get().strip()
        self.cmd_entry.delete(0, tk.END)
        if not code:
            return
        parts = code.split()
        cmd = parts[0].upper()

        # Markets commands
        if cmd == "MKT":
            # Async load with periodic refresh (15 seconds)
            self.load_view_async("MKT", view_markets, refresh_ms=180_000)
            return
        if cmd == "ADD" and len(parts) >= 2:
            sym = " ".join(parts[1:])
            added, msg = markets.add_ticker(sym)
            self.append_text(msg + "\n")
            # Re-render markets asynchronously
            self.load_view_async("MKT", view_markets, refresh_ms=15_000)
            return

        if cmd == "DEL" and len(parts) >= 2:
            sym = " ".join(parts[1:])
            ok, msg = markets.remove_ticker(sym)
            self.append_text(msg + "\n")
            # Re-render markets asynchronously
            self.load_view_async("MKT", view_markets, refresh_ms=15_000)
            return

        if cmd == "LIST":
            wl = markets.list_tickers()
            self.append_text("Watchlist: " + ", ".join(wl) + "\n")
            return

        # Fall back to router
        if cmd in VIEWS:
            self.load_view(cmd)
        else:
            self.append_text(f"[System] Unknown command '{code}'. Type HELP for options.\n")

        
        # --- Charts command (NEW) ---
        if cmd == "CHART":
            # CHART <ticker> [metric] [freq]
            if len(parts) >= 2:
                sym = parts[1]
                metric = parts[2] if len(parts) >= 3 else "MCAP"
                freq = parts[3] if len(parts) >= 4 else "Y"
                try:
                    charts.open_chart_window(self.root, sym, metric, freq)
                    self.status_right.configure(text=f"Chart: {sym} · {metric.upper()} ({freq.upper()})")
                except Exception as e:
                    self.append_text(f"[Error] {e}\n")
            else:
                self.append_text("Usage: CHART <ticker> [metric] [freq]\n")
            return


    def load_view(self, code: str):
        VIEW_LABELS = {
            "MKT": "Markets",
            "GFX": "Charts",
            "HELP": "Help",
            "N": "News",
            "FX": "FX",
            "FICC": "Fixed Income & Commodities",
            "CMDY": "Commodities",
            "EQS": "Equity Screener",
            "ECO": "Economic Calendar",
            "PORT": "Portfolio",
            "SET": "Settings",
        }
        fn = VIEWS.get(code)
        if not fn:
            return

        if code == "MKT":
            # Async + periodic refresh for a live feel
            self.load_view_async("MKT", fn, refresh_ms=180_000)
        else:
            # Synchronous for simple static views
            try:
                content = fn()
            except Exception as e:
                content = view_header(code) + f"[Error] {e}\n"
            self.set_text(content)
            label = VIEW_LABELS.get(code, "View")
            self.status_right.configure(text=f"Loaded: {code} ({label})")

    def clear(self):
        self.set_text("")
        self.status_right.configure(text="Cleared")

    def set_text(self, s: str):
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, s)
        self.text.see(tk.END)
        self.text.configure(state=tk.NORMAL)  # keep editable for selection

    def append_text(self, s: str, prefix=False):
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, s if not prefix else f"{s}")
        self.text.see(tk.END)
        self.text.configure(state=tk.NORMAL)

    def _on_close(self):
        try:
            self.executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TerminalApp()
    app.run()
