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

# --- Bloomberg Style Template ---

import plotly.io as pio

def register_bloomberg_like_template():
    # Accent palette (dark canvas, orange/blue series, neutral grid)
    # References: plotly_dark theming + Bloomberg brand color cues (orange/blue). 
    # See docs for templates & dark theme. (citations below)
    # - Built-in dark base: https://plotly.com/python/templates/
    # - Brand color references: https://mobbin.com/colors/brand/bloomberg
    # - Terminal charts overview: https://www.bloomberg.com/professional/products/bloomberg-terminal/charts/

    base = pio.templates["plotly_dark"].layout.to_plotly_json()

    base.update({
        "font": {"family": "Avenir, Inter, Helvetica, Arial, sans-serif", "size": 12, "color": "#E5E5E5"},
        "paper_bgcolor": "#0B0B0B",  # slightly deeper than plotly_dark
        "plot_bgcolor":  "#0B0B0B",
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0.0},
        "xaxis": {
            "gridcolor": "#1F1F1F", "linecolor": "#707070",
            "tickcolor": "#707070", "ticks": "outside", "tickformat": "%Y"
        },
        "yaxis": {
            "gridcolor": "#1F1F1F", "linecolor": "#707070",
            "tickcolor": "#707070", "ticks": "outside", "tickprefix": "$", "tickformat": ",~s"
        },
        "margin": {"l": 50, "r": 20, "t": 60, "b": 40},
    })

    # Default bar colors: annual (orange), quarterly (electric blue)
    # (You can still override per trace.)
    pio.templates["bloomberg_like"] = pio.templates["plotly_dark"]
    pio.templates["bloomberg_like"].layout.update(base)
    return "bloomberg_like"

# Register once on import
BLOOMBERG_TMPL = register_bloomberg_like_template()

