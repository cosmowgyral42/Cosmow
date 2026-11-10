import threading
import time
from collections import deque

# Limits are per client IP and route group, within a rolling 60-second window.
# Reads and writes have separate budgets so normal navigation does not consume
# the same small allowance as document mutations.
_LIMITS = {
    "login": (10, 60),
    "register": (5, 60),
    "ai": (20, 60),
    "documents_read": (60, 60),
    "documents_write": (20, 60),
    "rag": (15, 60),
}

_events: dict[tuple[str, str], deque[float]] = {}
_lock = threading.Lock()


def check_rate_limit(
    client_key: str,
    path: str,
    method: str = "GET",
) -> int | None:
    """Return retry-after seconds when limited; otherwise return None."""
    method = method.upper()

    if path == "/api/v1/auth/login":
        group = "login"
    elif path == "/api/v1/auth/register":
        group = "register"
    elif path.startswith("/api/v1/ai"):
        group = "ai"
    elif path.startswith("/api/v1/documents"):
        if method == "GET":
            group = "documents_read"
        elif method in {"POST", "DELETE"}:
            group = "documents_write"
        else:
            return None
    elif path.startswith("/api/v1/rag"):
        group = "rag"
    else:
        return None

    limit, window = _LIMITS[group]
    now = time.monotonic()
    key = (client_key, group)

    with _lock:
        events = _events.setdefault(key, deque())

        while events and now - events[0] >= window:
            events.popleft()

        if len(events) >= limit:
            return max(1, int(window - (now - events[0]) + 0.999))

        events.append(now)

        # Bound memory use if many distinct client IPs contact the server.
        if len(_events) > 10_000:
            cutoff = now - max(item[1] for item in _LIMITS.values())
            expired = [
                entry for entry, timestamps in _events.items()
                if not timestamps or timestamps[-1] <= cutoff
            ]
            for entry in expired:
                _events.pop(entry, None)

    return None


def reset_rate_limits() -> None:
    """Reset counters for isolated tests."""
    with _lock:
        _events.clear()
