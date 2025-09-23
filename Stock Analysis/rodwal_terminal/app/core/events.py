# app/core/events.py
from collections import defaultdict
from typing import Callable, Dict, List, Any

class EventBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable[..., None]]] = defaultdict(list)

    def on(self, topic: str, fn: Callable[..., None]):
        self._subs[topic].append(fn)

    def emit(self, topic: str, **payload: Any):
        for fn in self._subs.get(topic, []):
            try:
                fn(**payload)
            except Exception:
                pass
