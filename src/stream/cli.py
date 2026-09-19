from stream.args import parse_args
import logging
import queue
import threading
from stream.guard import acquire_process_mutex, kernel32
from stream.pipeline import Pipeline
from multiprocessing.connection import AuthenticationError, Listener
from typing import Any
import json

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s][%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 1.0


class LatestLogQueue:
    def __init__(self, maxsize: int) -> None:
        self._items: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, item: dict[str, Any]) -> None:
        with self._lock:
            if self._items.full():
                try:
                    self._items.get_nowait()
                except queue.Empty:
                    pass
            self._items.put_nowait(item)

    def get(self, timeout: float) -> dict[str, Any]:
        return self._items.get(timeout=timeout)


class PipeLogHandler(logging.Handler):
    def __init__(self, log_queue: LatestLogQueue) -> None:
        super().__init__()
        self._log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message: dict[str, Any] = {
                "type": "log",
                "created_at": record.created,
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                message["exception"] = logging.Formatter().formatException(
                    record.exc_info
                )
            self._log_queue.put(message)
        except Exception:
            self.handleError(record)


class StreamProcess:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._connection_ready = threading.Event()
        self._connection_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._connection: Any | None = None
        self._log_queue = LatestLogQueue(maxsize=1_000)
        self._log_handler = PipeLogHandler(self._log_queue)
        self._log_sender = threading.Thread(
            target=self._sendLogs,
            name="stream-pipe-log-sender",
            daemon=True,
        )
        self._heartbeat_sender = threading.Thread(
            target=self._sendHeartbeats,
            name="stream-pipe-heartbeat",
            daemon=True,
        )
        self._pipeline: Pipeline | None = None

    def run(self, arguments: Any) -> None:
        pipe_name = rf"\\.\pipe\pipe-works-stream-{arguments.process_id}"
        shared_secret = b"pipe-works-local-ipc-secret-v1"
        listener = Listener(
            address=pipe_name,
            family="AF_PIPE",
            authkey=shared_secret,
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(self._log_handler)
        self._log_sender.start()
        self._heartbeat_sender.start()
        self._pipeline = Pipeline(arguments)
        self._pipeline.start()

        try:
            while not self._stop_event.is_set():
                try:
                    connection = listener.accept()
                except (AssertionError, AuthenticationError):
                    logger.warning("Pipe 연결이 중단되어 다시 대기합니다.")
                    continue
                try:
                    self._setConnection(connection)
                    self._receiveMessages(connection)
                except EOFError:
                    logger.info("Supervisor Pipe 연결이 종료되었습니다.")
                finally:
                    self._clearConnection(connection)
                    connection.close()
        finally:
            self._stop_event.set()
            if self._pipeline is not None:
                self._pipeline.stop()
            root_logger.removeHandler(self._log_handler)
            listener.close()
            self._log_sender.join(timeout=1.0)
            self._heartbeat_sender.join(timeout=1.0)

    def _receiveMessages(self, connection: Any) -> None:
        while not self._stop_event.is_set():
            raw_message = connection.recv_bytes()
            message = json.loads(raw_message.decode("utf-8"))
            logger.debug("Supervisor Pipe 메시지: %s", message)

            message_type = message.get("type")
            if message_type == "hello":
                self._sendMessage(connection, {"type": "ready"})
            elif message_type == "stop":
                self._sendMessage(connection, {"type": "stopping"})
                self._stop_event.set()

    def _setConnection(self, connection: Any) -> None:
        with self._connection_lock:
            self._connection = connection
            self._connection_ready.set()

    def _clearConnection(self, connection: Any) -> None:
        with self._connection_lock:
            if self._connection is connection:
                self._connection = None
                self._connection_ready.clear()

    def _getConnection(self) -> Any | None:
        with self._connection_lock:
            return self._connection

    def _sendLogs(self) -> None:
        while not self._stop_event.is_set():
            if not self._connection_ready.wait(timeout=0.2):
                continue

            try:
                message = self._log_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            connection = self._getConnection()
            if connection is None:
                self._log_queue.put(message)
                continue

            try:
                self._sendMessage(connection, message)
            except (BrokenPipeError, EOFError, OSError):
                self._log_queue.put(message)
                self._clearConnection(connection)

    def _sendHeartbeats(self) -> None:
        while not self._stop_event.wait(HEARTBEAT_INTERVAL_SECONDS):
            connection = self._getConnection()
            if connection is None:
                continue
            try:
                self._sendMessage(connection, {"type": "heartbeat"})
            except (BrokenPipeError, EOFError, OSError):
                self._clearConnection(connection)

    def _sendMessage(self, connection: Any, message: dict[str, Any]) -> None:
        encoded_message = json.dumps(message).encode("utf-8")
        with self._send_lock:
            connection.send_bytes(encoded_message)


def main() -> None:
    arguments = parse_args()
    mutex = acquire_process_mutex(arguments.process_id)
    try:
        StreamProcess().run(arguments)
    finally:
        kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
