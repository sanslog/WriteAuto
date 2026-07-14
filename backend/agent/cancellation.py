"""Cross-thread cancellation token registry for generation sessions.

Each generation gets a threading.Event keyed by gen_id.
The SSE generator checks is_cancelled() between LLM chunks;
cancel_generation() sets the event to signal immediate stop.
"""

import asyncio
import threading

_lock = threading.Lock()
_events: dict[str, threading.Event] = {}
_async_events: dict[str, asyncio.Event] = {}


def register(gen_id: str) -> None:
    with _lock:
        _events[gen_id] = threading.Event()
        try:
            loop = asyncio.get_running_loop()
            _async_events[gen_id] = asyncio.Event()
        except RuntimeError:
            pass


def unregister(gen_id: str) -> None:
    with _lock:
        _events.pop(gen_id, None)
        _async_events.pop(gen_id, None)


def cancel(gen_id: str) -> None:
    with _lock:
        e = _events.get(gen_id)
        if e:
            e.set()
        ae = _async_events.get(gen_id)
        if ae:
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    loop.call_soon_threadsafe(ae.set)
            except RuntimeError:
                pass


def is_cancelled(gen_id: str) -> bool:
    with _lock:
        e = _events.get(gen_id)
        return e.is_set() if e else False


def get_async_event(gen_id: str) -> asyncio.Event | None:
    with _lock:
        return _async_events.get(gen_id)
