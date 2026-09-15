from pathlib import Path
from typing import Any

import torch
import os
import yaml
import logging
import importlib.util
import argparse
from types import ModuleType
from dataclasses import replace

from nvidia_pipe.receive import receive
from nvidia_pipe.decode import decode
from nvidia_pipe.encode import encode
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
        if not isinstance(rtsp, dict) or not rtsp.get("url") or not rtsp.get("transport"):
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
    raise TypeError(
        f"지원하지 않는 인코더 패킷 타입: {type(encoded).__name__}"
    )


def run_pipeline(config_path: str | Path | None = None) -> None:
    global sender

    config = load_config(str(config_path or "application.yml"))
    validate_config(config)
    configure_pipeline_logging(config["name"].strip())

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
        frame_index = 0
        for frame in frames:
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
                    if processed_frame is not None:
                        yield processed_frame
                except Exception as error:
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


def run_pipeline_entry(config_path: str | Path | None = None) -> None:
    try:
        run_pipeline(config_path)
    except KeyboardInterrupt:
        logger.info("사용자 요청으로 종료합니다.")
    finally:
        if sender is not None:
            sender.stop()



def main() -> None:
    args = parse_args()
    run_pipeline_entry(args.config)


if __name__ == "__main__":
    main()
