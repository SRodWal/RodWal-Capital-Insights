# --- Bloomberg Style Template ---

import plotly.io as pio
import numpy as np

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

def human_biz(num: float) -> str:
    """
    Format numbers with business suffixes: k, M, B, T (base 1000).
    Examples: 1_200 -> 1.2k; 3_400_000 -> 3.4M; 5_600_000_000 -> 5.6B
    """
    if num is None:
        return ""
    sign = "-" if num < 0 else ""
    n = abs(float(num))
    for div, suf in [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "k")]:
        if n >= div:
            return f"{sign}{n/div:.2f}".rstrip("0").rstrip(".") + suf
    return f"{sign}{n:.0f}"

def apply_business_ticks(fig):
    # Get y-range from current data
    all_y = []
    for tr in fig.data:
        if hasattr(tr, "y") and tr.y is not None:
            all_y.extend(list(tr.y))
    if not all_y:
        return

    ymin, ym = 0, max(all_y)
    # Generate ~6 ticks from 0 to max
    ticks = np.linspace(ymin, ym, 6)
    tickvals = list(ticks)
    ticktext = [human_biz(v) for v in tickvals]

    fig.update_yaxes(tickmode="array", tickvals=tickvals, ticktext=ticktext)



# Register once on import
BLOOMBERG_TMPL = register_bloomberg_like_template()