import tkinter as tk
from tkinter import ttk
from datetime import datetime

# --------------------------
# Simple Mock Bloomberg Terminal (Tkinter)
# --------------------------

# --- RodWal Color Palette ---
BG_DARK = "#001E40"        # Main background
BG_PANEL = "#001E40"       # Panels same as main for consistency
FG_TEXT = "#F5F5F5"        # Contrast text
FG_MUTED = "#d0d0d0"       # Slightly muted for secondary text

# Accents
ACCENT_AMBER = "#F39C12"   # Secondary 2 (Amber) - highlights, key buttons
ACCENT_GREEN = "#2C6E49"   # Secondary 3 (Green) - positive indicators
ACCENT_RED = "#8B1E3F"     # Secondary 1 (Crimson) - warnings, quit
ACCENT_BLUE = "#2C6E49"    # Using green for info (or keep blue if needed)
ACCENT_PURPLE = "#8B1E3F"  # Reuse crimson for utilities if needed

# Fonts
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_LABEL = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas", 10)  # content area


# --- Dummy view builders (placeholder content) ---
def view_header(title: str) -> str:
    banner = f"=== {title} ==="
    line = "-" * len(banner)
    return f"{banner}\n{line}\n"

def view_markets():
    return (
        view_header("Market Monitor (MKT)") +
        "INDEX        LAST     CHG     CHG%    TIME\n"
        "--------------------------------------------\n"
        "SPX          5,324.7  +12.6   +0.24%  15:12\n"
        "NDX         18,214.3  +58.2   +0.32%  15:12\n"
        "DJI         39,281.9  +45.5   +0.12%  15:12\n"
        "VIX             12.7  -0.3    -2.31%  15:12\n"
        "\nTip: Type 'EQS' for Equity Screener or 'FX' for FX dashboard.\n"
    )

def view_news():
    return (
        view_header("Top News (N)") +
        "• Futures steady as investors await central bank remarks.\n"
        "• Oil edges higher on supply concerns.\n"
        "• Semiconductor names extend gains on strong demand outlook.\n"
        "\nTip: Type 'ECO' for Economic Calendar.\n"
    )

def view_fx():
    return (
        view_header("FX Dashboard (FX)") +
        "PAIR     LAST      CHG     CHG%\n"
        "--------------------------------\n"
        "EURUSD   1.0875    +0.0012  +0.11%\n"
        "USDJPY   147.28    -0.22    -0.15%\n"
        "GBPUSD   1.2791    +0.0008  +0.06%\n"
        "USDMXN   16.78     -0.05    -0.30%\n"
    )

def view_ficc():
    return (
        view_header("Fixed Income & Commodities (FICC)") +
        "UST 10Y  3.97%  (-3 bps)\n"
        "UST 2Y   4.22%  (-1 bp)\n"
        "WTI      82.14  (+0.6%)\n"
        "Gold     2,415  (+0.2%)\n"
    )

def view_cmdy():
    return (
        view_header("Commodities (CMDY)") +
        "CONTRACT   LAST     CHG    CHG%\n"
        "--------------------------------\n"
        "WTI        82.14    +0.51  +0.63%\n"
        "BRENT      85.00    +0.48  +0.57%\n"
        "Copper     4.15     +0.02  +0.49%\n"
        "NatGas     2.61     -0.01  -0.38%\n"
    )

def view_eqs():
    return (
        view_header("Equity Screener (EQS)") +
        "Filter: Region=US | MktCap>10B | Momentum>0\n"
        "-------------------------------------------\n"
        "Ticker   Name                     MktCap    Mom(1M)\n"
        "---------------------------------------------------\n"
        "AAPL     Apple Inc.               3.5T      +4.1%\n"
        "MSFT     Microsoft Corp.          3.8T      +3.2%\n"
        "NVDA     NVIDIA Corp.             2.9T      +7.4%\n"
        "AMZN     Amazon.com Inc.          2.1T      +5.3%\n"
    )

def view_eco():
    return (
        view_header("Economic Calendar (ECO)") +
        "Today (Local):\n"
        "• 08:30  Initial Jobless Claims\n"
        "• 09:45  PMI (Flash)\n"
        "• 10:00  Existing Home Sales\n"
        "\nUpcoming:\n"
        "• Mon    CPI (YoY)\n"
        "• Wed    FOMC Rate Decision\n"
    )

def view_port():
    return (
        view_header("Portfolio (PORT)") +
        "Name: Core Multi-Asset (Mock)\n"
        "PnL (D):     +$12,450\n"
        "PnL (MTD):   +$62,130\n"
        "Exposure:\n"
        "  - Equity:       62%\n"
        "  - Fixed Income: 28%\n"
        "  - Cash:         10%\n"
    )

def view_help():
    return (
        view_header("Help (HELP)") +
        "Type a function mnemonic and press Enter, or click a button.\n"
        "Available mnemonics:\n"
        "  MKT, N, FX, FICC, CMDY, EQS, ECO, PORT, HELP, SET\n"
        "\nShortcuts:\n"
        "  F1 = Help | Ctrl+Q = Quit | Esc = Clear content\n"
    )

def view_settings():
    return (
        view_header("Settings (SET)") +
        "• Theme: Dark (default)\n"
        "• Font:  Consolas 10 (content)\n"
        "• Time:  Local system time\n"
        "\n(This is a mock; wire your own preferences here.)\n"
    )

# --- Router for commands -> views ---
VIEWS = {
    "MKT": view_markets,
    "N": view_news,
    "FX": view_fx,
    "FICC": view_ficc,
    "CMDY": view_cmdy,
    "EQS": view_eqs,
    "ECO": view_eco,
    "PORT": view_port,
    "HELP": view_help,
    "SET": view_settings,
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
        x, y, cx, cy = self.widget.bbox("insert") if self.widget == self.widget.focus_get() else (0, 0, 0, 0)
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
        label.pack(ipadx=8, ipy=4)

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
        self.root.title("Mock Bloomberg Terminal")
        self.root.geometry("1000x650")
        self.root.configure(bg=BG_DARK)

        # macOS: better looking titlebar when supported
        try:
            self.root.tk.call('tk', 'scaling', 1.2)
        except Exception:
            pass

        self._build_ui()
        self._bind_keys()
        self._tick_clock()

        # Show initial help screen
        self.load_view("HELP")

    # ---- UI ----
    def _build_ui(self):
        # Top Header
        header = tk.Frame(self.root, bg=BG_PANEL)
        header.pack(side=tk.TOP, fill=tk.X)

        title = tk.Label(
            header, text="●  RodWal Capital Strageties — Terminal",
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
            b = tk.Button(
                buttons_panel, text=f"{label}",
                command=(self.root.destroy if code == "QUIT" else lambda c=code: self.load_view(c)),
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

        self.cmd_entry = tk.Entry(cmd_bar, bg="#1a1c22", fg=FG_TEXT, insertbackground=FG_TEXT, width=20, font=FONT_LABEL, relief=tk.FLAT)
        self.cmd_entry.pack(side=tk.LEFT, padx=8)
        self.cmd_entry.bind("<Return>", self._on_enter)

        hint = tk.Label(cmd_bar, text="Try: MKT, N, FX, FICC, CMDY, EQS, ECO, PORT, HELP, SET", bg=BG_DARK, fg=FG_MUTED, font=("Segoe UI", 9))
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

        self.status_left = tk.Label(status, text="Connected - YFinance", bg=BG_PANEL, fg=ACCENT_GREEN, font=FONT_LABEL)
        self.status_left.pack(side=tk.LEFT, padx=12, pady=6)

        self.status_right = tk.Label(status, text="Ready", bg=BG_PANEL, fg=FG_MUTED, font=FONT_LABEL)
        self.status_right.pack(side=tk.RIGHT, padx=12)

    # ---- Key bindings & clock ----
    def _bind_keys(self):
        self.root.bind("<Escape>", lambda e: self.clear())
        self.root.bind("<F1>", lambda e: self.load_view("HELP"))
        self.root.bind("<Control-q>", lambda e: self.root.destroy())

    def _tick_clock(self):
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.time_label.configure(text=now)
        self.root.after(1000, self._tick_clock)

    # ---- Actions ----
    def _on_enter(self, _event=None):
        code = self.cmd_entry.get().strip().upper()
        self.cmd_entry.delete(0, tk.END)
        if not code:
            return
        if code in VIEWS:
            self.load_view(code)
        else:
            self.append_text(
                f"[System] Unknown command '{code}'. Type HELP for options.\n",
                prefix=True
            )

    def load_view(self, code: str):
        fn = VIEWS.get(code)
        if not fn:
            return
        content = fn()
        self.set_text(content)
        self.status_right.configure(text=f"Loaded view: {code}")

    def clear(self):
        self.set_text("")
        self.status_right.configure(text="Cleared")

    def set_text(self, s: str):
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, s)
        self.text.see(tk.END)
        self.text.configure(state=tk.NORMAL)  # keep editable off? prefer NORMAL for selection

    def append_text(self, s: str, prefix=False):
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, s if not prefix else f"{s}")
        self.text.see(tk.END)
        self.text.configure(state=tk.NORMAL)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = TerminalApp()
    app.run()
