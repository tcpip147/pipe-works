import asyncio
import threading
from collections import defaultdict, deque
from typing import Any


class ProcessEventBroker:
    """Delivers process events only to browser sessions subscribed to that process."""

    def __init__(self, max_queue_size: int = 200) -> None:
        self._max_queue_size = max_queue_size
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = (
            defaultdict(set)
        )
        self._history: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=max_queue_size)
        )
        self._status_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = threading.Lock()

    def subscribeStatus(self) -> asyncio.Queue[dict[str, Any]]:
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=self._max_queue_size
        )
        loop = asyncio.get_running_loop()
        with self._lock:
            if self._loop is None:
                self._loop = loop
            elif self._loop is not loop:
                raise RuntimeError("ProcessEventBroker must use one event loop.")
            self._status_subscribers.add(event_queue)
        return event_queue

    def unsubscribeStatus(self, event_queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._status_subscribers.discard(event_queue)

    def subscribe(self, process_id: str) -> asyncio.Queue[dict[str, Any]]:
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=self._max_queue_size
        )
        loop = asyncio.get_running_loop()
        with self._lock:
            if self._loop is None:
                self._loop = loop
            elif self._loop is not loop:
                raise RuntimeError("ProcessEventBroker must use one event loop.")
            self._subscribers[process_id].add(event_queue)
            history = tuple(self._history.get(process_id, ()))

        for event in history:
            event_queue.put_nowait(event)
        return event_queue

    def unsubscribe(
        self,
        process_id: str,
        event_queue: asyncio.Queue[dict[str, Any]],
    ) -> None:
        with self._lock:
            subscribers = self._subscribers.get(process_id)
            if subscribers is None:
                return
            subscribers.discard(event_queue)
            if not subscribers:
                self._subscribers.pop(process_id, None)

    def publish(self, event: dict[str, Any]) -> None:
        process_id = event.get("process_id")
        if not isinstance(process_id, str):
            return

        with self._lock:
            self._history[process_id].append(event)
            loop = self._loop
            subscribers = tuple(self._subscribers.get(process_id, ()))
        if loop is None or not subscribers:
            return

        for event_queue in subscribers:
            loop.call_soon_threadsafe(self._putLatest, event_queue, event)

    def publishStatus(self, event: dict[str, Any]) -> None:
        with self._lock:
            loop = self._loop
            subscribers = tuple(self._status_subscribers)
        if loop is None or not subscribers:
            return

        for event_queue in subscribers:
            loop.call_soon_threadsafe(self._putLatest, event_queue, event)

    @staticmethod
    def _putLatest(
        event_queue: asyncio.Queue[dict[str, Any]],
        event: dict[str, Any],
    ) -> None:
        if event_queue.full():
            try:
                event_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        event_queue.put_nowait(event)
