"""Cross-thread cancellation token registry for generation sessions.

Each generation gets a threading.Event keyed by gen_id.
The SSE generator checks is_cancelled() between LLM chunks;
cancel_generation() sets the event to signal immediate stop.
"""

import threading

_lock = threading.Lock()
_events: dict[str, threading.Event] = {}


def register(gen_id: str) -> None:
    with _lock:
        _events[gen_id] = threading.Event()


def unregister(gen_id: str) -> None:
    with _lock:
        _events.pop(gen_id, None)


def cancel(gen_id: str) -> None:
    with _lock:
        e = _events.get(gen_id)
        if e:
            e.set()


def is_cancelled(gen_id: str) -> bool:
    with _lock:
        e = _events.get(gen_id)
        return e.is_set() if e else False
