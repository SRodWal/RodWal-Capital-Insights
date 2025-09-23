# plugins/example_markets/plugin.py
from app.core.theme import ACCENT_AMBER
from app.core.registry import PluginSpec, ButtonSpec

def _view_header(title: str) -> str:
    banner = f"=== {title} ==="
    line = "-" * len(banner)
    return f"{banner}
{line}
"

def render_markets() -> str:
    return (
        _view_header("Market Monitor (MKT)")
        + "INDEX        LAST     CHG     CHG%    TIME
"
          "--------------------------------------------
"
          "SPX          5,324.7  +12.6   +0.24%  15:12
"
          "NDX         18,214.3  +58.2   +0.32%  15:12
"
          "DJI         39,281.9  +45.5   +0.12%  15:12
"
          "VIX             12.7  -0.3    -2.31%  15:12
"
          "
Tip: Type 'EQS' for Equity Screener or 'FX' for FX dashboard.
"
    )

def register(app):
    """
    Called by the loader. Return a PluginSpec.
    """
    return PluginSpec(
        code="MKT",
        name="Markets",
        render=render_markets,
        button=ButtonSpec(label="Markets", color=ACCENT_AMBER, tip="Market Monitor"),
        aliases=["MARKETS", "MARKET"],
        defaults={"refresh_sec": 30}
    )
