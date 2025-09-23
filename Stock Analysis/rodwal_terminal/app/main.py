# app/main.py
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from app.core import theme
from app.core.registry import PluginRegistry, discover_plugins
from app.core.events import EventBus
from app.core.log import get_logger

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
        tw.wm_geometry(f"+{x}+{y}")

    def _hide(self, _event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class AppContext:
    def __init__(self, root):
        self.root = root
        self.logger = get_logger()
        self.events = EventBus()
        self.registry = PluginRegistry(self)  # filled by discover_plugins

class TerminalApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RodWal Terminal — MOCK")
        self.root.geometry("1000x650")
        self.root.configure(bg=theme.BG_DARK)
        try:
            self.root.tk.call('tk', 'scaling', 1.2)
        except Exception:
            pass

        # App context & plugins
        self.ctx = AppContext(self.root)
        discover_plugins(self.ctx, package="plugins")
        self._build_ui()
        self._bind_keys()
        self._tick_clock()

        # Initial page: Help/Welcome
        self._show_welcome()

        # Start plugin background jobs (if any)
        self.ctx.registry.start_background()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI ----
    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=theme.BG_PANEL)
        header.pack(side=tk.TOP, fill=tk.X)
        title = tk.Label(header, text="●  RodWal Terminal — MOCK",
                         bg=theme.BG_PANEL, fg=theme.FG_TEXT, font=theme.FONT_TITLE)
        title.pack(side=tk.LEFT, padx=12, pady=10)
        self.time_label = tk.Label(header, text="--:--:--",
                                   bg=theme.BG_PANEL, fg=theme.FG_MUTED, font=theme.FONT_LABEL)
        self.time_label.pack(side=tk.RIGHT, padx=12)

        # Dynamic Buttons (from plugins)
        self.buttons_panel = tk.Frame(self.root, bg=theme.BG_DARK)
        self.buttons_panel.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(8, 4))
        self._rebuild_buttons()

        # Command Bar
        cmd_bar = tk.Frame(self.root, bg=theme.BG_DARK)
        cmd_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(6, 8))
        lbl = tk.Label(cmd_bar, text="Command:", bg=theme.BG_DARK, fg=theme.FG_MUTED, font=theme.FONT_LABEL)
        lbl.pack(side=tk.LEFT)
        self.cmd_entry = tk.Entry(cmd_bar, bg="#0b1a33", fg=theme.FG_TEXT, insertbackground=theme.FG_TEXT,
                                  width=20, font=theme.FONT_LABEL, relief=tk.FLAT)
        self.cmd_entry.pack(side=tk.LEFT, padx=8)
        self.cmd_entry.bind("<Return>", self._on_enter)
        hint = tk.Label(cmd_bar,
                        text="Type a code (e.g. MKT) or click a button. F1=Help, Ctrl+Q=Quit",
                        bg=theme.BG_DARK, fg=theme.FG_MUTED, font=("Segoe UI", 9))
        hint.pack(side=tk.LEFT, padx=10)

        # Content Panel
        content_frame = tk.Frame(self.root, bg=theme.BG_DARK)
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        self.text = tk.Text(content_frame, wrap=tk.NONE, bg="#08162c", fg=theme.FG_TEXT,
                            insertbackground=theme.FG_TEXT, relief=tk.FLAT, font=theme.FONT_MONO, undo=False)
        yscroll = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.text.yview)
        xscroll = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=self.text.xview)
        self.text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # Status Bar
        status = tk.Frame(self.root, bg=theme.BG_PANEL)
        status.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_left = tk.Label(status, text="Ready (mock)", bg=theme.BG_PANEL,
                                    fg=theme.ACCENT_GREEN, font=theme.FONT_LABEL)
        self.status_left.pack(side=tk.LEFT, padx=12, pady=6)
        self.status_right = tk.Label(status, text="", bg=theme.BG_PANEL,
                                     fg=theme.FG_MUTED, font=theme.FONT_LABEL)
        self.status_right.pack(side=tk.RIGHT, padx=12)

        # Quit button (always present)
        qb = tk.Button(self.buttons_panel, text="QUIT",
                       command=self.root.destroy, bg=theme.ACCENT_RED, fg="black",
                       activebackground=theme.ACCENT_RED, activeforeground="black",
                       relief=tk.FLAT, font=theme.FONT_BUTTON, padx=14, pady=6, cursor="hand2")
        qb.pack(side=tk.RIGHT, padx=6, pady=4)
        ToolTip(qb, "Exit Application")

    def _rebuild_buttons(self):
        # Clear current buttons
        for child in self.buttons_panel.winfo_children():
            child.destroy()
        # Build buttons from registered plugins
        for spec in self.ctx.registry.all():
            if spec.button:
                b = tk.Button(
                    self.buttons_panel, text=spec.button.label,
                    command=lambda c=spec.code: self.load_view(c),
                    bg=spec.button.color, fg="black",
                    activebackground=spec.button.color, activeforeground="black",
                    relief=tk.FLAT, font=theme.FONT_BUTTON, padx=14, pady=6, cursor="hand2",
                )
                b.pack(side=tk.LEFT, padx=6, pady=4)
                ToolTip(b, f"{spec.button.tip}  ·  Mnemonic: {spec.code}")

    # ---- Key bindings & clock ----
    def _bind_keys(self):
        self.root.bind("<Escape>", lambda e: self.clear())
        self.root.bind("<F1>", lambda e: self._show_welcome())
        self.root.bind("<Control-q>", lambda e: self.root.destroy())

    def _tick_clock(self):
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.time_label.configure(text=now)
        self.root.after(1000, self._tick_clock)

    # ---- Actions ----
    def _on_enter(self, _event=None):
        token = self.cmd_entry.get().strip()
        self.cmd_entry.delete(0, tk.END)
        if not token:
            return
        self.load_view(token)

    def load_view(self, token: str):
        spec = self.ctx.registry.resolve(token)
        if not spec:
            self.append_text(f"[System] Unknown command '{token}'. Press F1 for help.
")
            return
        try:
            content = spec.render()  # str
        except Exception as ex:
            content = f"[Error] Failed to render '{spec.code}': {ex}
"
        self.set_text(content)
        self.status_right.configure(text=f"Loaded: {spec.code} ({spec.name})")

    def _show_welcome(self):
        content = (
            "=== RodWal Terminal — Welcome ===
"
            "---------------------------------
"
            "This is the initial screen. Add modules as plugins under /plugins.

"
            "How to use:
"
            "• Click a button above (generated by plugins), or
"
            "• Type a mnemonic (e.g., MKT) in the Command box and press Enter.

"
            "Developer tips:
"
            "• Add a plugin at plugins/<your_module>/plugin.py with register(app).
"
            "• The register() should return a PluginSpec with code, name, and render().
"
            "• Use app.events.emit()/on() for decoupled communication.
"
        )
        self.set_text(content)
        self.status_right.configure(text="Welcome")

    def clear(self):
        self.set_text("")
        self.status_right.configure(text="Cleared")

    def set_text(self, s: str):
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, s)
        self.text.see(tk.END)
        self.text.configure(state=tk.NORMAL)

    def append_text(self, s: str):
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, s)
        self.text.see(tk.END)
        self.text.configure(state=tk.NORMAL)

    def _on_close(self):
        # Stop plugin background tasks
        try:
            self.ctx.registry.stop_background()
        finally:
            self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    TerminalApp().run()
