import argparse
import importlib.util
import logging
import os
import json
import threading
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import torch
import yaml

from nvidia_pipe.decode import decode
from nvidia_pipe.encode import encode
import nvidia_pipe.receive as receive_module
from nvidia_pipe.receive import receive
from nvidia_pipe.send import Sender, is_idr_keyframe


class PipelineNameFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__()
        self.pipeline_name = "-"

    def filter(self, record: logging.LogRecord) -> bool:
        record.pipeline_name = self.pipeline_name
        return True


PIPELINE_NAME_FILTER = PipelineNameFilter()

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(pipeline_name)s] %(asctime)s %(levelname)s [%(name)s] %(message)s",
)
for handler in logging.getLogger().handlers:
    handler.addFilter(PIPELINE_NAME_FILTER)


logger = logging.getLogger(__name__)

sender = None

# Per-pipeline counters. They are reset when a pipeline starts so callers can
# inspect the live totals for the currently running pipeline.
received_frame_count = 0
sent_frame_count = 0
inference_success_frame_count = 0
inference_failure_frame_count = 0
STATISTICS_INTERVAL_SECONDS = 1


def reset_frame_counters() -> None:
    """Reset the global counters for a newly started pipeline."""
    global received_frame_count
    global sent_frame_count
    global inference_success_frame_count
    global inference_failure_frame_count
    received_frame_count = 0
    sent_frame_count = 0
    inference_success_frame_count = 0
    inference_failure_frame_count = 0
    receive_module.reset_out_of_order_frame_count()


def frame_statistics() -> dict[str, int]:
    """Return a snapshot of the current pipeline frame counters."""
    return {
        "received_frame_count": received_frame_count,
        "sent_frame_count": sent_frame_count,
        "inference_success_frame_count": inference_success_frame_count,
        "inference_failure_frame_count": inference_failure_frame_count,
        "out_of_order_frame_count": receive_module.out_of_order_frame_count,
    }


def send_frame_statistics(endpoint: str) -> None:
    """Send the current counter snapshot to the supervising plumber process."""
    request = Request(
        endpoint,
        data=json.dumps(frame_statistics()).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=1):
            pass
    except (OSError, URLError) as error:
        logger.warning("Could not report frame statistics: %s", error)


def start_statistics_reporter(
    endpoint: str,
) -> tuple[threading.Event, threading.Thread]:
    """Report frame statistics every second until stopped."""
    stop_event = threading.Event()

    def report() -> None:
        while not stop_event.wait(STATISTICS_INTERVAL_SECONDS):
            send_frame_statistics(endpoint)

    thread = threading.Thread(target=report, name="frame-statistics", daemon=True)
    thread.start()
    return stop_event, thread


def configure_pipeline_logging(name: str) -> None:
    """Expose the configured YAML name at the front of every log record."""
    PIPELINE_NAME_FILTER.pipeline_name = name


def load_config(path: str) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def validate_config(config: dict[str, Any]) -> None:
    name = config.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Pipeline configuration requires a non-empty name")
    for section in ("input", "output", "inference"):
        if not isinstance(config.get(section), dict):
            raise ValueError(f"필수 설정 섹션이 없습니다: {section}")
    for section in ("input", "output"):
        rtsp = config[section].get("rtsp")
        if (
            not isinstance(rtsp, dict)
            or not rtsp.get("url")
            or not rtsp.get("transport")
        ):
            raise ValueError(f"필수 RTSP 설정이 없습니다: {section}.rtsp")
    inference = config["inference"]
    required = ("gpuid", "interval_frames", "input_format", "frame_type", "model")
    missing = [key for key in required if key not in inference]
    if missing:
        raise ValueError(f"필수 추론 설정이 없습니다: {', '.join(missing)}")
    if int(inference["interval_frames"]) < 0:
        raise ValueError("interval_frames는 0 이상이어야 합니다")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NVIDIA video pipeline")
    parser.add_argument(
        "-c",
        "--config",
        help="YAML 설정 파일 경로",
    )
    return parser.parse_args()


def load_module(path: str | Path) -> ModuleType:
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location(
        path.stem,
        path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"모듈을 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_cuda_dll_path() -> None:
    cuda_paths = [
        os.environ.get("CUDA_PATH"),
        os.environ.get("CUDA_PATH_V12_6"),
    ]
    for cuda_path in filter(None, cuda_paths):
        for directory in (
            Path(cuda_path) / "bin",
            Path(cuda_path) / "bin" / "x64",
        ):
            if directory.is_dir() and hasattr(os, "add_dll_directory"):
                os.add_dll_directory(str(directory))


def encoded_bytes(encoded) -> bytes:
    if isinstance(encoded, (bytes, bytearray, memoryview)):
        return bytes(encoded)
    if isinstance(encoded, dict):
        for key in ("bitstream", "data", "packet", "encoded_data", "payload"):
            if key in encoded:
                value = encoded[key]
                if isinstance(value, (bytes, bytearray, memoryview)):
                    return bytes(value)
                if isinstance(value, (list, tuple)):
                    return bytes(value)
        for value in encoded.values():
            if isinstance(value, (bytes, bytearray, memoryview)):
                return bytes(value)
            if isinstance(value, (dict, list, tuple)):
                try:
                    return encoded_bytes(value)
                except TypeError:
                    continue
    if isinstance(encoded, (list, tuple)):
        if all(isinstance(value, int) for value in encoded):
            return bytes(encoded)
        for value in encoded:
            try:
                return encoded_bytes(value)
            except TypeError:
                continue
    raise TypeError(f"지원하지 않는 인코더 패킷 타입: {type(encoded).__name__}")


def run_pipeline(config_path: str | Path | None = None) -> None:
    global sender
    global received_frame_count
    global sent_frame_count
    global inference_success_frame_count
    global inference_failure_frame_count

    config = load_config(str(config_path or "application.yml"))
    validate_config(config)
    configure_pipeline_logging(config["name"].strip())
    reset_frame_counters()

    inference = config["inference"]
    gpuid = int(inference["gpuid"])
    interval_frames = int(inference["interval_frames"])
    frame_type = inference["frame_type"]
    model = inference["model"]
    configure_cuda_dll_path()
    model_module = load_module(model)

    sender = Sender(config, heartbeat_timeout=10)
    sender.start()

    packets = receive(config)
    pipeline_stream = torch.cuda.Stream(device=gpuid)
    frames = decode(config, packets, cuda_stream=pipeline_stream)

    def processed_frames():
        global received_frame_count
        global inference_success_frame_count
        global inference_failure_frame_count

        frame_index = 0
        for frame in frames:
            received_frame_count += 1
            if interval_frames == 0:
                yield frame
            else:
                should_infer = frame_index % interval_frames == 0
                try:
                    if frame_type == "pytorch":
                        with torch.cuda.stream(pipeline_stream), torch.inference_mode():
                            processed_frame = model_module.on_frame(
                                frame, infer=should_infer
                            )
                    else:
                        raise ValueError(f"지원하지 않는 프레임 타입: {frame_type}")
                    frame_index += 1
                    if should_infer:
                        inference_success_frame_count += 1
                    if processed_frame is not None:
                        yield processed_frame
                except Exception as error:
                    if should_infer:
                        inference_failure_frame_count += 1
                    logger.debug("추론 실패: %s", error)
                    yield frame

    packets = encode(processed_frames(), cuda_stream=pipeline_stream)

    for packet in packets:
        packet_data = encoded_bytes(packet.packet_data)
        cpu_packet = replace(
            packet,
            packet_data=packet_data,
            is_keyframe=is_idr_keyframe(packet.codec, packet_data),
        )

        sender.submit(cpu_packet)
        sent_frame_count += 1


def run_pipeline_entry(
    config_path: str | Path | None = None, statistics_endpoint: str | None = None
) -> None:
    reporter = None
    try:
        if statistics_endpoint is not None:
            reporter = start_statistics_reporter(statistics_endpoint)
        run_pipeline(config_path)
    except KeyboardInterrupt:
        logger.info("사용자 요청으로 종료합니다.")
    finally:
        if reporter is not None:
            stop_event, thread = reporter
            stop_event.set()
            thread.join(timeout=1)
            if statistics_endpoint is not None:
                send_frame_statistics(statistics_endpoint)
        if sender is not None:
            sender.stop()


def main() -> None:
    args = parse_args()
    run_pipeline_entry(args.config)


if __name__ == "__main__":
    main()
