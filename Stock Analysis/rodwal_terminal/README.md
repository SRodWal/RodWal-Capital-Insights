# RodWal Terminal — Modular Mock Terminal (Tkinter)

This is a **plugin-ready** mock terminal in Tkinter using the **RodWal** color palette.

## Quick Start

```bash
python -m app.main
```

> Requires Python 3.9+ and Tk (on Linux: `sudo apt-get install python3-tk`).

## Structure

```
rodwal_terminal/
├─ app/
│  ├─ main.py               # Entry point (Tkinter app)
│  └─ core/
│     ├─ theme.py           # RodWal color palette & fonts
│     ├─ registry.py        # PluginSpec, registry & loader
│     ├─ events.py          # Lightweight event bus (pub/sub)
│     ├─ config.py          # Settings loader
│     └─ log.py             # Logging config
├─ plugins/
│  ├─ __init__.py
│  └─ example_markets/
│     ├─ __init__.py
│     └─ plugin.py          # Example plugin
├─ config/
│  └─ settings.json         # User settings
├─ assets/
│  └─ logo.png              # Placeholder logo
└─ README.md
```

## How Plugins Work

Each plugin is a folder with a `plugin.py` that exposes a `register(app)` function returning a `PluginSpec`.

Minimal example:

```python
from app.core.registry import PluginSpec, ButtonSpec

def render() -> str:
    return "Hello from my plugin!"

def register(app):
    return PluginSpec(
        code="HELLO",
        name="Hello",
        render=render,
        button=ButtonSpec(label="Hello", color="#F39C12", tip="Say hello"),
        aliases=["HI"],
    )
```

Place it under `plugins/my_hello/plugin.py`. On app start, it will be discovered and its button will appear.

## Run Tips

- **F1** — Welcome/Help
- **Ctrl+Q** — Quit
- **Esc** — Clear content panel
- **Command box** — type a mnemonic like `MKT` then Enter

## Notes

- This project does not fetch live data; all content is placeholder. You can wire plugins to your data sources later.
- The app writes logs to `logs/app.log`.
