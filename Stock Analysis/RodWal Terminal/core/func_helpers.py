


# ----------- Plot helpers -----------
def _format_currency(y, pos=None):
    """Compact currency formatter in billions: 1e9 -> $1.23B."""
    if y is None:
        return ""
    magnitude = abs(y)
    if magnitude >= 1e12:
        return f"{y/1e12:,.2f}T"
    if magnitude >= 1e9:
        return f"{y/1e9:,.2f}B"
    if magnitude >= 1e6:
        return f"{y/1e6:,.2f}M"
    return f"{y:,.0f}"
