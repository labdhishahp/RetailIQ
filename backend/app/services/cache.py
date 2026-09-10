"""Small in-process TTL cache for analytics responses.

Analytics recompute a year of aggregates on every call; without this the
dashboard's parallel fan-out on mount hammers the database. Cleared on any
write so figures never go stale after an operation.
"""

import threading
import time
from typing import Any, Callable

from app.core.config import settings

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}


def cached(key: str, producer: Callable[[], Any], ttl: int | None = None) -> Any:
    ttl = settings.analytics_cache_seconds if ttl is None else ttl
    if ttl <= 0:
        return producer()
    now = time.time()
    with _lock:
        hit = _store.get(key)
        if hit and hit[0] > now:
            return hit[1]
    value = producer()
    with _lock:
        _store[key] = (now + ttl, value)
    return value


def invalidate(prefix: str = "") -> int:
    with _lock:
        keys = [k for k in _store if k.startswith(prefix)] if prefix else list(_store)
        for k in keys:
            _store.pop(k, None)
        return len(keys)


def stats() -> dict:
    with _lock:
        return {"entries": len(_store)}
