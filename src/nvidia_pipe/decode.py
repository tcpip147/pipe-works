from collections.abc import Iterator
import logging
from typing import Any
from statistics import median
import torch

from nvidia_pipe.stream import ReceivedPacket
from nvidia_pipe.stream import GpuFrame

logger = logging.getLogger(__name__)


def calculate_fps(frame_buffer, time_base) -> float | None:
    pts_list = [frame.getPTS() for frame in frame_buffer if frame.getPTS() is not None]

    if len(pts_list) < 2:
        return None

    deltas = [
        current - previous
        for previous, current in zip(pts_list, pts_list[1:])
        if current > previous
    ]

    if not deltas:
        return None

    average_delta = median(deltas)

    return 1.0 / (average_delta * float(time_base))


def decode(
    config: dict[str, Any],
    packets: Iterator[ReceivedPacket],
    cuda_stream: torch.cuda.Stream | None = None,
) -> Iterator[GpuFrame]:
    import PyNvVideoCodec as nvc

    decoder = None
    pixel_format = None
    time_base = None

    for packet in packets:
        if decoder is None:
            gpuid = int(config["inference"]["gpuid"])

            input_format = config["inference"]["input_format"]
            if input_format == "native":
                output_format = nvc.OutputColorType.NATIVE
            elif input_format == "rgb":
                output_format = nvc.OutputColorType.RGB
            elif input_format == "rgbp":
                output_format = nvc.OutputColorType.RGBP
            else:
                raise ValueError(f"Unsupported input_format: {input_format}")

            time_base = packet.input_stream.time_base

            decoder_kwargs = {
                "gpuid": gpuid,
                "codec": packet.codec,
                "usedevicememory": True,
                "outputColorType": output_format,
                "latency": nvc.DisplayDecodeLatencyType.NATIVE,
            }
            if cuda_stream is not None:
                decoder_kwargs["cudastream"] = cuda_stream.cuda_stream

            decoder = nvc.CreateDecoder(
                **decoder_kwargs,
            )

            pixel_format = decoder.GetPixelFormat()
            logger.info("NVDEC 디코더 초기화: gpu=%s codec=%s", gpuid, packet.codec)

        decoded_frames = decoder.Decode(packet.packet_data)
        for frame_data in decoded_frames:
            yield GpuFrame(
                gpuid,
                packet.codec.name.lower(),
                packet.input_stream.width,
                packet.input_stream.height,
                pixel_format.name,
                time_base,
                packet.input_stream.average_rate,
                frame_data.getPTS(),
                frame_data,
            )
