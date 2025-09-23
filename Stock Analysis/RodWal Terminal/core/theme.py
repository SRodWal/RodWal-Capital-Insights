# app/core/theme.py
# RodWal Color Palette + fonts

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
