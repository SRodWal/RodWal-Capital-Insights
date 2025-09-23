# app/core/config.py
import json
import os
from typing import Any, Dict

DEFAULTS = {
    "plugins": {"enabled": "*"},
}

def load_settings(path: str = "config/settings.json") -> Dict[str, Any]:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULTS.copy()
    return DEFAULTS.copy()
