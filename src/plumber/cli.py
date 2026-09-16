"""HTTP control server for RTSP pipeline processes."""

from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import yaml

from nvidia_pipe.cli import run_pipeline_entry

logger = logging.getLogger(__name__)
INDEX_PAGE_PATH = Path(__file__).with_name("index.html")


@dataclass(frozen=True)
class PipelineDefinition:
    name: str
    config_path: Path


class PipelineManager:
    def __init__(self, config_path: str | Path) -> None:
        self._config_path = Path(config_path).resolve()
        self._definitions = self._load_definitions(self._config_path)
        self._port = self._load_port(self._config_path)
        self._auto_start = self._load_auto_start(self._config_path)
        self._processes: dict[str, BaseProcess] = {}
        self._stopped: set[str] = set()
        self._statistics: dict[str, dict[str, int | str]] = {}
        self._lock = threading.RLock()
        self._context = mp.get_context("spawn")

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as file:
            document = yaml.safe_load(file)
        if not isinstance(document, dict):
            raise ValueError(f"Expected a YAML mapping: {path}")
        return document

    @classmethod
    def _load_definitions(cls, plumber_path: Path) -> dict[str, PipelineDefinition]:
        pipelines = cls._load_yaml(plumber_path).get("pipelines")
        if not isinstance(pipelines, list):
            raise ValueError("plumber configuration requires a pipelines list")
        definitions = {}
        for index, item in enumerate(pipelines, 1):
            config = item.get("config") if isinstance(item, dict) else None
            if not isinstance(config, str) or not config.strip():
                raise ValueError(f"Pipeline {index} requires a configuration file path")
            path = (plumber_path.parent / config).resolve()
            name = cls._load_yaml(path).get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Pipeline configuration requires a name: {path}")
            name = name.strip()
            if name in definitions:
                raise ValueError(f"Duplicate pipeline name: {name}")
            definitions[name] = PipelineDefinition(name, path)
        return definitions

    @classmethod
    def _load_port(cls, plumber_path: Path) -> int:
        port = cls._load_yaml(plumber_path).get("port")
        if (
            isinstance(port, bool)
            or not isinstance(port, int)
            or not 1 <= port <= 65535
        ):
            raise ValueError(
                "plumber configuration requires a port between 1 and 65535"
            )
        return port

    @classmethod
    def _load_auto_start(cls, plumber_path: Path) -> bool:
        auto_start = cls._load_yaml(plumber_path).get("auto_start", False)
        if not isinstance(auto_start, bool):
            raise ValueError("plumber auto_start must be true or false")
        return auto_start

    @property
    def port(self) -> int:
        return self._port

    @property
    def auto_start(self) -> bool:
        return self._auto_start

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self.status(name) for name in sorted(self._definitions)]

    def status(self, name: str) -> dict[str, Any]:
        with self._lock:
            definition = self._definitions.get(name)
            if definition is None:
                raise KeyError(name)
            process = self._processes.get(name)
            if process is None:
                state, exit_code = "stopped", None
            elif process.is_alive():
                state, exit_code = "running", None
            else:
                state, exit_code = (
                    ("stopped" if name in self._stopped else "failed"),
                    process.exitcode,
                )
            return {
                "name": name,
                "state": state,
                "pid": process.pid if process else None,
                "exit_code": exit_code,
                "config": str(definition.config_path),
                "statistics": self._statistics.get(name, self._empty_statistics()).copy(),
            }

    @staticmethod
    def _empty_statistics() -> dict[str, int | str]:
        return {
            "received_frame_count": 0,
            "sent_frame_count": 0,
            "inference_success_frame_count": 0,
            "inference_failure_frame_count": 0,
            "out_of_order_frame_count": 0,
            "input_rtsp_status": "disconnected",
            "output_rtsp_status": "disconnected",
        }

    def start(self, name: str) -> dict[str, Any]:
        with self._lock:
            if name not in self._definitions:
                raise KeyError(name)
            existing = self._processes.get(name)
            if existing is not None and existing.is_alive():
                return self.status(name)
            if existing is not None:
                existing.join(timeout=0)
            process = self._context.Process(
                target=run_pipeline_entry,
                args=(
                    str(self._definitions[name].config_path),
                    f"http://127.0.0.1:{self._port}/api/pipelines/{quote(name)}/statistics",
                ),
                name=name,
            )
            process.start()
            self._processes[name] = process
            self._stopped.discard(name)
            self._statistics[name] = self._empty_statistics()
            logger.info("Started pipeline %s (pid=%s)", name, process.pid)
            return self.status(name)

    def start_all(self) -> list[dict[str, Any]]:
        """Start every configured pipeline, leaving running processes untouched."""
        return [self.start(name) for name in sorted(self._definitions)]

    def start_configured_pipelines(self) -> list[dict[str, Any]]:
        """Start all pipelines only when plumber.yml opts into auto-start."""
        return self.start_all() if self.auto_start else []

    def stop(self, name: str) -> dict[str, Any]:
        with self._lock:
            if name not in self._definitions:
                raise KeyError(name)
            process = self._processes.get(name)
            self._stopped.add(name)
            if process is not None and process.is_alive():
                logger.info("Stopping pipeline %s (pid=%s)", name, process.pid)
                process.terminate()
                process.join(timeout=3)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=2)
            return self.status(name)

    def record_statistics(self, name: str, statistics: dict[str, Any]) -> dict[str, Any]:
        counters = {
            "received_frame_count",
            "sent_frame_count",
            "inference_success_frame_count",
            "inference_failure_frame_count",
            "out_of_order_frame_count",
        }
        statuses = {"input_rtsp_status", "output_rtsp_status"}
        required = counters | statuses
        if name not in self._definitions:
            raise KeyError(name)
        if not isinstance(statistics, dict) or set(statistics) != required or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for key, value in statistics.items()
            if key in counters
        ) or any(
            not isinstance(statistics[key], str)
            or statistics[key]
            not in {"disconnected", "connected"}
            for key in statuses
        ):
            raise ValueError("invalid frame statistics")
        with self._lock:
            self._statistics[name] = statistics.copy()
            return self.status(name)

    def stop_all(self) -> None:
        for name in list(self._definitions):
            self.stop(name)


def make_handler(manager: PipelineManager) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: HTTPStatus, payload: Any) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                body = INDEX_PAGE_PATH.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/api/pipelines":
                self._send_json(HTTPStatus.OK, manager.list())
            elif path.startswith("/api/pipelines/"):
                try:
                    self._send_json(
                        HTTPStatus.OK,
                        manager.status(unquote(path.removeprefix("/api/pipelines/"))),
                    )
                except KeyError:
                    self._send_json(
                        HTTPStatus.NOT_FOUND, {"error": "pipeline not found"}
                    )
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:
            parts = [
                unquote(part) for part in urlparse(self.path).path.split("/") if part
            ]
            if parts == ["api", "pipelines", "start-all"]:
                self._send_json(HTTPStatus.OK, manager.start_all())
                return
            if (
                len(parts) == 4
                and parts[:2] == ["api", "pipelines"]
                and parts[3] == "statistics"
            ):
                try:
                    content_length = int(self.headers.get("Content-Length", "0"))
                    statistics = json.loads(self.rfile.read(content_length))
                    self._send_json(
                        HTTPStatus.OK, manager.record_statistics(parts[2], statistics)
                    )
                except KeyError:
                    self._send_json(
                        HTTPStatus.NOT_FOUND, {"error": "pipeline not found"}
                    )
                except (ValueError, json.JSONDecodeError):
                    self._send_json(
                        HTTPStatus.BAD_REQUEST, {"error": "invalid frame statistics"}
                    )
                return
            if (
                len(parts) != 4
                or parts[:2] != ["api", "pipelines"]
                or parts[3] not in {"start", "stop"}
            ):
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                self._send_json(
                    HTTPStatus.OK,
                    (
                        manager.start(parts[2])
                        if parts[3] == "start"
                        else manager.stop(parts[2])
                    ),
                )
            except KeyError:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "pipeline not found"})

        def log_message(self, format: str, *args: object) -> None:
            logger.debug("HTTP %s - %s", self.address_string(), format % args)

    return Handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pipe-works HTTP control server")
    parser.add_argument(
        "-c", "--config", default="plumber.yml", help="Pipeline list YAML path"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manager = PipelineManager(args.config)
    manager.start_configured_pipelines()
    server = ThreadingHTTPServer((args.host, manager.port), make_handler(manager))
    logger.info(
        "Pipeline control server listening at http://%s:%s", args.host, manager.port
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping pipeline control server")
    finally:
        server.server_close()
        manager.stop_all()


if __name__ == "__main__":
    main()
