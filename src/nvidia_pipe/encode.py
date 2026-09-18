from collections.abc import Iterator
from fractions import Fraction
import logging
from nvidia_pipe.stream import GpuFrame
from nvidia_pipe.stream import EncodedPacket
import torch

logger = logging.getLogger(__name__)


def encoder_fps(frame: GpuFrame) -> int:
    """Return the nearest whole output FPS for the source stream."""
    if frame.frame_rate is None or frame.frame_rate <= 0:
        logger.warning("Input FPS is unavailable; falling back to 30 FPS")
        return 30
    return max(1, round(float(frame.frame_rate)))


def encode(
    frames: Iterator[GpuFrame],
    cuda_stream: torch.cuda.Stream | None = None,
) -> Iterator[EncodedPacket]:
    """GPU 프레임을 순차적으로 NVENC 패킷으로 변환하고 종료 패킷을 배출한다."""
    import PyNvVideoCodec as nvc

    encoder = None
    codec = None
    width = None
    height = None
    output_time_base = None
    for frame in frames:
        if encoder is None:
            fps = encoder_fps(frame)
            # NVENC returns packet timestamps in its output-frame clock.  Do
            # not pair those values with the input RTSP clock (commonly
            # 1/90000), otherwise a timestamp increment of one is interpreted
            # as 1/90000 second rather than one encoded frame.
            output_time_base = Fraction(1, fps)
            encoder_kwargs = {
                "gpu_id": frame.gpuid,
                "codec": frame.codec,
                "bf": 0,
                # Match the input FPS and emit one IDR about every second.
                "fps": fps,
                "gop": fps,
                "idrperiod": fps,
            }
            if cuda_stream is not None:
                encoder_kwargs["cudastream"] = cuda_stream.cuda_stream
            encoder = nvc.CreateEncoder(
                frame.width,
                frame.height,
                frame.pixel_format,
                False,
                **encoder_kwargs,
            )

            codec = frame.codec
            width = frame.width
            height = frame.height
            logger.info(
                "NVENC 인코더 초기화: gpu=%s codec=%s fps=%s idrperiod=%s",
                frame.gpuid,
                frame.codec,
                fps,
                fps,
            )

        with torch.cuda.stream(cuda_stream):
            packets = encoder.Encode(frame.frame_data)

        for packet_data in packets:
            yield EncodedPacket(
                codec,
                width,
                height,
                output_time_base,
                packet_data.get("timestamp"),
                packet_data,
            )

    if encoder is not None:
        packets = encoder.EndEncode()

        for packet_data in packets:
            yield EncodedPacket(
                codec,
                width,
                height,
                output_time_base,
                packet_data.get("timestamp"),
                packet_data,
            )
