import logging
import sqlite3
from conductor.process.process_repository import ProcessRepository
from conductor.process.windows_process import WindowsProcessLocator
from conductor.process.stream_connection import StreamConnection
from collections.abc import Callable
from typing import Any
import subprocess
import sys
import time
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


shared_secret = b"pipe-works-local-ipc-secret-v1"
HEARTBEAT_TIMEOUT_SECONDS = 3.0
HEARTBEAT_CHECK_INTERVAL_SECONDS = 0.5


class ProcessAlreadyExistsError(Exception):
    pass


class InvalidProcessError(Exception):
    pass


class ProcessNotFoundError(Exception):
    pass


class ProcessNotRunningError(Exception):
    pass


class Supervisor:
    def __init__(self) -> None:
        self._repository = ProcessRepository()
        self._process_locator = WindowsProcessLocator()
        self._children: dict[str, StreamConnection] = {}
        self._children_lock = threading.Lock()
        self._event_publisher: Callable[[dict[str, Any]], None] | None = None
        self._status_publisher: Callable[[dict[str, Any]], None] | None = None
        self._heartbeat_lock = threading.Lock()
        self._last_heartbeats: dict[str, float] = {}
        self._process_statuses: dict[str, str] = {}

        for process in self._repository.getAll():
            self._openChild(process["id"])

        threading.Thread(
            target=self._monitorHeartbeats,
            name="stream-heartbeat-monitor",
            daemon=True,
        ).start()

    def setEventPublisher(
        self,
        event_publisher: Callable[[dict[str, Any]], None],
    ) -> None:
        self._event_publisher = event_publisher

    def setStatusPublisher(
        self,
        status_publisher: Callable[[dict[str, Any]], None],
    ) -> None:
        self._status_publisher = status_publisher

    def _monitorHeartbeats(self) -> None:
        while True:
            time.sleep(HEARTBEAT_CHECK_INTERVAL_SECONDS)
            now = time.monotonic()
            with self._heartbeat_lock:
                expired_process_ids = [
                    process_id
                    for process_id, last_heartbeat in self._last_heartbeats.items()
                    if now - last_heartbeat > HEARTBEAT_TIMEOUT_SECONDS
                ]
            for process_id in expired_process_ids:
                self._setProcessStatus(process_id, "stopped")

    def _setProcessStatus(self, process_id: str, status: str) -> None:
        with self._heartbeat_lock:
            previous_status = self._process_statuses.get(process_id, "stopped")
            self._process_statuses[process_id] = status

        if previous_status != status and self._status_publisher is not None:
            self._status_publisher(
                {
                    "type": "process_status",
                    "process_id": process_id,
                    "state": status,
                    "input_state": status,
                    "output_state": status,
                }
            )

    def _getProcessStatus(self, process_id: str) -> str:
        with self._heartbeat_lock:
            return self._process_statuses.get(process_id, "stopped")

    def _createPipeName(self, process_id: str) -> str:
        return rf"\\.\pipe\pipe-works-stream-{process_id}"

    def _openChild(self, process_id: str, attempts: int = 1) -> bool:
        with self._children_lock:
            child = self._children.get(process_id)
            if child is not None and child.isOpen:
                return True

        for attempt in range(attempts):
            child = StreamConnection(
                pipe_name=self._createPipeName(process_id),
                shared_secret=shared_secret,
                onConnected=lambda connection: self._onConnected(
                    process_id, connection
                ),
                onClose=lambda connection: self._onClose(process_id, connection),
                onError=lambda connection, error: self._onError(
                    process_id, connection, error
                ),
                onMessage=lambda connection, message: self._onMessage(
                    process_id, connection, message
                ),
            )
            if child.open():
                with self._children_lock:
                    self._children[process_id] = child
                child.send({"type": "hello"})
                return True

            if attempt + 1 < attempts:
                time.sleep(0.5)

        return False

    def _onConnected(self, process_id: str, connection: StreamConnection) -> None:
        logger.info("StreamProcess Pipe 연결됨: %s", process_id)

    def _onClose(self, process_id: str, connection: StreamConnection) -> None:
        with self._children_lock:
            if self._children.get(process_id) is connection:
                self._children.pop(process_id)
        self._setProcessStatus(process_id, "stopped")
        logger.info("StreamProcess Pipe 연결 종료: %s", process_id)

    def _onError(
        self,
        process_id: str,
        connection: StreamConnection,
        error: Exception,
    ) -> None:
        logger.warning("StreamProcess Pipe 오류 [%s]: %s", process_id, error)

    def _onMessage(
        self,
        process_id: str,
        connection: StreamConnection,
        message: dict[str, Any],
    ) -> None:
        if message.get("type") == "heartbeat":
            with self._heartbeat_lock:
                self._last_heartbeats[process_id] = time.monotonic()
            self._setProcessStatus(process_id, "running")
            return

        if message.get("type") == "log":
            if self._event_publisher is not None:
                self._event_publisher({**message, "process_id": process_id})
            return

    def addProcess(self, process: dict[str, Any]) -> None:
        record = self._makeRecord(process)
        try:
            self._repository.add(record)
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorcode in (
                sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
                sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            ):
                raise ProcessAlreadyExistsError(
                    "같은 이름의 프로세스가 이미 존재합니다."
                ) from error
            raise

    def updateProcess(self, process_id: str, process: dict[str, Any]) -> None:
        record = self._makeRecord(process)
        if not self._repository.update(process_id, record):
            raise ProcessNotFoundError("프로세스를 찾을 수 없습니다.")

    def _makeRecord(self, process: dict[str, Any]) -> dict[str, Any]:
        if process["inference_enabled"] and not process["inference_module"].strip():
            raise InvalidProcessError("Inference의 Module path를 입력해주세요.")
        return {
            "id": process["name"],
            "input_rtsp_url": process["input_rtsp_url"],
            "input_transport": process["input_transport"],
            "input_jitter_buffer": int(process["jitter_buffer"]),
            "output_rtsp_url": process["output_rtsp_url"],
            "output_transport": process["output_transport"],
            "metadata_enabled": int(process["metadata_enabled"]),
            "metadata_module_path": process["metadata_module"],
            "inference_enabled": int(process["inference_enabled"]),
            "inference_gpuid": int(process["gpuid"]),
            "inference_interval_frames": int(process["interval_frames"]),
            "inference_input_format": process["input_format"],
            "inference_frame_type": process["frame_type"],
            "inference_module_path": process["inference_module"],
            "postprocess_enabled": int(process["postprocess_enabled"]),
            "postprocess_module_path": process["postprocess_module"],
            "desired_state": "running" if process["desired_state"] else "stopped",
            "sequence": int(process["sequence"]),
        }

    def getProcesses(self) -> list[dict]:
        processes = self._repository.getAll()
        return [
            {
                **process,
                "state": self._getProcessStatus(process["id"]),
                "input_state": self._getProcessStatus(process["id"]),
                "output_state": self._getProcessStatus(process["id"]),
            }
            for process in processes
        ]

    def deleteProcess(self, process_id: str) -> None:
        if not self._repository.delete(process_id):
            raise ProcessNotFoundError("프로세스를 찾을 수 없습니다.")

    def startProcess(self, process_id: str) -> None:
        process = self._repository.get(process_id)
        if process is None:
            raise ProcessNotFoundError("프로세스를 찾을 수 없습니다.")

        if self._process_locator.getProcessIds(process_id):
            return

        pythonw_executable = Path(sys.executable).with_name("pythonw.exe")
        executable = (
            str(pythonw_executable)
            if pythonw_executable.is_file()
            else sys.executable
        )
        if executable == sys.executable:
            logger.warning("pythonw.exe를 찾을 수 없어 python.exe로 실행합니다.")

        command = [
            executable,
            "-m",
            "stream.cli",
            "--process-id",
            process_id,
            "--input-rtsp-url",
            process["input_rtsp_url"],
            "--input-transport",
            process["input_transport"],
            "--input-jitter-buffer",
            str(process["input_jitter_buffer"]),
            "--output-rtsp-url",
            process["output_rtsp_url"],
            "--output-transport",
            process["output_transport"],
        ]

        logger.info("프로세스 시작: %s", subprocess.list2cmdline(command))

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        handle = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            ),
            startupinfo=startupinfo,
            close_fds=True,
        )

        if not self._openChild(process_id, attempts=20):
            handle.terminate()
            raise RuntimeError(f"StreamProcess Pipe 연결 시간 초과: {process_id}")

    def stopProcess(self, process_id: str) -> None:
        if self._repository.get(process_id) is None:
            raise ProcessNotFoundError("프로세스를 찾을 수 없습니다.")

        with self._children_lock:
            child = self._children.get(process_id)
        if child is not None and child.isOpen:
            child.send({"type": "stop"})
            return

        process_ids = self._process_locator.getProcessIds(process_id)

        if not process_ids:
            raise ProcessNotRunningError("실행 중인 프로세스가 없습니다.")

        for pid in process_ids:
            result = subprocess.run(
                ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 128:
                continue
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    result.args,
                    output=result.stdout,
                    stderr=result.stderr,
                )
