import av
import time
import ctypes
import logging
from collections.abc import Iterator
from typing import Any

from nvidia_pipe.stream import ReceivedPacket

logger = logging.getLogger(__name__)

# 순서 이상 프레임 수집 주기 (초)
TIMESTAMP_ANOMALY_LOG_INTERVAL_SECONDS = 5.0


def receive(config: dict[str, Any]) -> Iterator[ReceivedPacket]:
    import PyNvVideoCodec as nvc

    input_rtsp = config["input"]["rtsp"]
    url = input_rtsp["url"]
    transport = input_rtsp["transport"]

    codec_ids = {
        "h264": nvc.cudaVideoCodec.H264,
        "hevc": nvc.cudaVideoCodec.HEVC,
        "h265": nvc.cudaVideoCodec.HEVC,
    }
    timestamp_anomaly_count = 0
    next_timestamp_anomaly_log_at = (
        time.monotonic() + TIMESTAMP_ANOMALY_LOG_INTERVAL_SECONDS
    )

    while True:
        container = None

        try:
            logger.info(f"수신 RTSP 연결 시도")

            container = av.open(
                url,
                mode="r",
                options={"rtsp_transport": transport, "rw_timeout": "5000000"},
                timeout=(5.0, 5.0),
            )

            input_stream = container.streams.video[0]
            codec_name = input_stream.codec_context.name.lower()
            if codec_name not in codec_ids:
                logger.error("지원하지 않는 NVDEC 코덱: %s", codec_name)
                raise ValueError(f"Unsupported NVDEC codec: {codec_name}")
            codec = codec_ids[codec_name]

            logger.info(f"width: {input_stream.width}")
            logger.info(f"height: {input_stream.height}")
            logger.info(f"average_fps: {input_stream.average_rate}")
            logger.info(f"codec: {codec}")
            logger.info(
                f"time_base: {input_stream.time_base.numerator}/{input_stream.time_base.denominator}"
            )

            previous_pts = None

            for packet in container.demux(video=0):
                if not packet:
                    continue
                if packet.pts is None or packet.dts is None:
                    if previous_pts is not None:
                        logger.warning(
                            "이상 프레임 발생 : previous_pts=%s, pts=%s, dts=%s",
                            previous_pts,
                            packet.pts,
                            packet.dts,
                        )
                    continue
                packet_data = nvc.PacketData()
                bitstream = ctypes.create_string_buffer(bytes(packet))
                packet_data.bsl_data = ctypes.addressof(bitstream)
                packet_data.bsl = len(bitstream) - 1
                packet_data.pts = packet.pts
                packet_data.dts = packet.dts
                if previous_pts is None:
                    packet_data.duration = packet.duration
                else:
                    duration = packet.pts - previous_pts
                    if duration <= 0:
                        timestamp_anomaly_count += 1
                    packet_data.duration = max(0, duration)
                packet_data.key = bool(packet.is_keyframe)
                packet_data.is_video = True

                previous_pts = packet.pts

                now = time.monotonic()
                if now >= next_timestamp_anomaly_log_at:
                    if timestamp_anomaly_count:
                        logger.debug(
                            "최근 %.0f초간 시간 순서 이상 프레임: %s건",
                            TIMESTAMP_ANOMALY_LOG_INTERVAL_SECONDS,
                            timestamp_anomaly_count,
                        )
                        timestamp_anomaly_count = 0
                    next_timestamp_anomaly_log_at = (
                        now + TIMESTAMP_ANOMALY_LOG_INTERVAL_SECONDS
                    )

                yield ReceivedPacket(codec, input_stream, packet_data, bitstream)

        except (av.FFmpegError, OSError, IndexError) as error:
            logger.error(f"수신 RTSP 연결 끊김")

        finally:
            if container is not None:
                container.close()

        delay = 3
        logger.warning(f"{delay}초 후 수신 서버에 재접속합니다.")
        time.sleep(delay)
