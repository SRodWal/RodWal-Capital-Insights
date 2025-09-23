# app/core/registry.py
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, List, Any
import importlib
import pkgutil
import traceback

@dataclass
class ButtonSpec:
    label: str
    color: str
    tip: str

@dataclass
class PluginSpec:
    # Required
    code: str                     # e.g., "MKT" mnemonic
    name: str                     # display name
    render: Callable[[], str]     # returns text content for the main panel

    # Optional UI integrations
    button: Optional[ButtonSpec] = None
    # Optional: background task starter, returns a stop callable
    start: Optional[Callable[[], Callable[[], None]]] = None
    # Optional: command aliases
    aliases: List[str] = field(default_factory=list)
    # Optional: settings schema/defaults
    defaults: Dict[str, Any] = field(default_factory=dict)

class PluginRegistry:
    def __init__(self, app_context):
        self._plugins: Dict[str, PluginSpec] = {}
        self._aliases: Dict[str, str] = {}
        self._stoppers: Dict[str, Callable[[], None]] = {}
        self.app = app_context

    def register(self, spec: PluginSpec):
        code = spec.code.upper()
        if code in self._plugins:
            raise ValueError(f"Duplicate plugin code: {code}")
        self._plugins[code] = spec
        for alias in spec.aliases:
            self._aliases[alias.upper()] = code
        self.app.logger.info(f"Registered plugin: {code} ({spec.name})")

    def resolve(self, token: str) -> Optional[PluginSpec]:
        token = token.upper().strip()
        code = self._aliases.get(token, token)
        return self._plugins.get(code)

    def all(self) -> List[PluginSpec]:
        return list(self._plugins.values())

    def start_background(self):
        for code, spec in self._plugins.items():
            if spec.start:
                try:
                    stopper = spec.start()
                    if callable(stopper):
                        self._stoppers[code] = stopper
                except Exception:
                    self.app.logger.error("Failed to start background for %s
%s", code, traceback.format_exc())

    def stop_background(self):
        for code, stop in self._stoppers.items():
            try:
                stop()
            except Exception:
                self.app.logger.error("Failed to stop background for %s
%s", code, traceback.format_exc())

def discover_plugins(app_context, package: str = "plugins"):
    """
    Discovers modules under the given package and calls `register(app)` inside each plugin module.
    Only files named `plugin.py` are considered (convention).
    """
    registry = app_context.registry
    pkg = importlib.import_module(package)
    for _, modname, ispkg in pkgutil.walk_packages(pkg.__path__, package + "."):
        if not modname.endswith(".plugin"):
            continue
        try:
            mod = importlib.import_module(modname)
            if hasattr(mod, "register") and callable(mod.register):
                spec = mod.register(app_context)
                registry.register(spec)
            else:
                app_context.logger.warning("Module %s has no register(app) function", modname)
        except Exception:
            app_context.logger.error("Failed loading plugin %s
%s", modname, traceback.format_exc())
    return registry
