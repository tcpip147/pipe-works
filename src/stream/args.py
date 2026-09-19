import argparse
from typing import Any


def parse_args() -> Any:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--process-id",
        required=True,
        help="Conductor에 등록된 프로세스 식별자",
    )
    parser.add_argument(
        "--input-rtsp-url",
        required=True,
        help="입력 RTSP URL",
    )
    parser.add_argument(
        "--input-transport",
        required=True,
        help="입력 RTSP 전송 타입",
    )
    parser.add_argument(
        "--input-jitter-buffer",
        type=int,
        default=30,
        help="입력 RTSP 전송 버퍼 크기",
    )
    parser.add_argument(
        "--output-rtsp-url",
        required=True,
        help="출력 RTSP URL",
    )
    parser.add_argument(
        "--output-transport",
        required=True,
        help="출력 RTSP 전송 타입",
    )
    return parser.parse_args()
