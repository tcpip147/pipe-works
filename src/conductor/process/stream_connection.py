import json
import logging
import threading
from collections.abc import Callable
from multiprocessing.connection import Client
from typing import Any

logger = logging.getLogger(__name__)

ConnectedHandler = Callable[["StreamConnection"], None]
ClosedHandler = Callable[["StreamConnection"], None]
ErrorHandler = Callable[["StreamConnection", Exception], None]
MessageHandler = Callable[["StreamConnection", dict[str, Any]], None]


class StreamConnection:
    def __init__(
        self,
        pipe_name: str,
        shared_secret: bytes,
        onConnected: ConnectedHandler,
        onClose: ClosedHandler,
        onError: ErrorHandler,
        onMessage: MessageHandler,
    ) -> None:
        self._pipe_name = pipe_name
        self._shared_secret = shared_secret
        self._on_connected = onConnected
        self._on_close = onClose
        self._on_error = onError
        self._on_message = onMessage
        self._connection: Any | None = None
        self._closing = False
        self._closed_notified = False
        self._lock = threading.Lock()

    @property
    def isOpen(self) -> bool:
        with self._lock:
            return self._connection is not None and not self._closing

    def open(self) -> bool:
        try:
            connection = Client(
                address=self._pipe_name,
                family="AF_PIPE",
                authkey=self._shared_secret,
            )
        except Exception as error:
            self._on_error(self, error)
            return False

        with self._lock:
            if self._closing:
                connection.close()
                return False
            self._connection = connection

        self._on_connected(self)
        threading.Thread(
            target=self._receiveLoop,
            name="stream-pipe-receiver",
            daemon=True,
        ).start()
        return True

    def close(self) -> None:
        with self._lock:
            self._closing = True
            connection = self._connection
            self._connection = None

        if connection is not None:
            connection.close()

    def send(self, message: dict[str, Any]) -> None:
        encoded_message = json.dumps(message).encode("utf-8")
        with self._lock:
            connection = self._connection
            if connection is None or self._closing:
                raise RuntimeError("StreamProcess Pipe 연결이 없습니다.")
            connection.send_bytes(encoded_message)

    def _receiveLoop(self) -> None:
        try:
            while True:
                with self._lock:
                    connection = self._connection
                    closing = self._closing
                if connection is None or closing:
                    return

                raw_message = connection.recv_bytes()
                try:
                    message = json.loads(raw_message.decode("utf-8"))
                    if not isinstance(message, dict):
                        raise ValueError("Pipe 메시지는 JSON 객체여야 합니다.")
                    self._on_message(self, message)
                except Exception as error:
                    self._on_error(self, error)
        except EOFError:
            pass
        except Exception as error:
            with self._lock:
                closing = self._closing
            if not closing:
                self._on_error(self, error)
        finally:
            self._notifyClosed()

    def _notifyClosed(self) -> None:
        with self._lock:
            if self._closed_notified:
                return
            self._closed_notified = True
            self._connection = None

        self._on_close(self)
