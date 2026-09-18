from __future__ import annotations
from multiprocessing.synchronize import Event as ProcessEvent

from collections.abc import Iterator
from typing import Any
import logging
import multiprocessing as mp
import queue as queue_module
import threading
import time

import av

from nvidia_pipe.stream import EncodedPacket

logger = logging.getLogger(__name__)


def is_idr_keyframe(codec: str, packet_data: bytes) -> bool:
    """Return whether an Annex-B encoded access unit contains a recovery IDR."""
    normalized_codec = codec.lower()
    if normalized_codec not in {"h264", "h265", "hevc"}:
        return False

    offset = 0
    size = len(packet_data)
    while offset + 3 < size:
        start = packet_data.find(b"\x00\x00\x01", offset)
        if start < 0:
            return False
        header = start + 3
        if start > 0 and packet_data[start - 1] == 0:
            header = start + 3
        if header >= size:
            return False

        nal_type = (
            packet_data[header] & 0x1F
            if normalized_codec == "h264"
            else (packet_data[header] >> 1) & 0x3F
        )
        if normalized_codec == "h264" and nal_type == 5:
            return True
        if normalized_codec in {"h265", "hevc"} and nal_type in {19, 20}:
            return True
        offset = header + 1

    return False


class Sender:
    def __init__(
        self,
        config: dict[str, Any],
        *,
        queue_size: int = 30,
        heartbeat_timeout: float = 10,
    ) -> None:
        self._config = config
        self._queue = mp.Queue(maxsize=queue_size)
        self._heartbeat = mp.Value("d", time.monotonic())
        self._has_successful_mux = mp.Value("b", False)
        self._awaiting_mux = mp.Value("b", True)
        self._heartbeat_timeout = heartbeat_timeout
        self._monitor_stop = threading.Event()
        self._lock = threading.Lock()
        self._process: mp.Process | None = None
        self._worker_stop: ProcessEvent | None = None
        self._monitor: threading.Thread | None = None

    def start(self) -> None:
        with self._lock:
            self._start_process()

        self._monitor = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="rtsp-sender-monitor",
        )
        self._monitor.start()

    def submit(self, packet: EncodedPacket) -> None:
        try:
            self._queue.put(packet, timeout=1)
        except queue_module.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(packet)
            except (queue_module.Empty, queue_module.Full):
                pass

    def stop(self) -> None:
        self._monitor_stop.set()
        if self._monitor is not None:
            self._monitor.join(timeout=2)

        with self._lock:
            self._stop_process()

        self._queue.cancel_join_thread()
        self._queue.close()

    @property
    def connection_status(self) -> str:
        """Return output RTSP health from successful-mux heartbeat state."""
        if not self._has_successful_mux.value:
            return "disconnected"
        if self._awaiting_mux.value:
            return "disconnected"
        if self._process is None or not self._process.is_alive():
            return "disconnected"
        if time.monotonic() - self._heartbeat.value >= self._heartbeat_timeout:
            return "disconnected"
        return "connected"

    def _monitor_loop(self) -> None:
        while not self._monitor_stop.wait(1):
            with self._lock:
                if self._process is None:
                    continue

                stalled = (
                    time.monotonic() - self._heartbeat.value >= self._heartbeat_timeout
                )
                if not self._process.is_alive() or stalled:
                    reason = "응답없음" if stalled else "정지됨"
                    logger.error("송신 RTSP %s; 재연결 시도: %s초", reason, self._heartbeat_timeout)
                    self._stop_process()
                    if not self._monitor_stop.is_set():
                        self._start_process()

    def _start_process(self) -> None:
        self._worker_stop = mp.Event()
        self._heartbeat.value = time.monotonic()
        self._awaiting_mux.value = True
        self._process = mp.Process(
            target=send_worker,
            args=(
                self._queue,
                self._config,
                self._heartbeat,
                self._has_successful_mux,
                self._awaiting_mux,
                self._worker_stop,
            ),
            name="rtsp-sender",
            daemon=True,
        )
        self._process.start()

    def _stop_process(self) -> None:
        if self._process is None:
            return

        if self._worker_stop is not None:
            self._worker_stop.set()
        self._process.join(timeout=1)

        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=2)

        if self._process.is_alive():
            self._process.kill()
            self._process.join(timeout=2)

        if self._process.is_alive():
            logger.error("RTSP sender could not be reaped after kill request")

        self._process = None
        self._worker_stop = None


def queue_packets(packet_queue, shutdown_event) -> Iterator[EncodedPacket]:
    while not shutdown_event.is_set():
        try:
            packet = packet_queue.get(timeout=0.5)
        except queue_module.Empty:
            continue

        if packet is None:
            return
        yield packet


def send_worker(
    packet_queue, config, heartbeat, has_successful_mux, awaiting_mux, shutdown_event
) -> None:
    name = config.get("name") if isinstance(config, dict) else None
    if isinstance(name, str) and name.strip():
        # The sender is spawned independently, so it must initialize its own
        # process-local logging filter rather than inheriting the parent's value.
        from nvidia_pipe.cli import configure_pipeline_logging

        configure_pipeline_logging(name.strip())
    send(
        config,
        queue_packets(packet_queue, shutdown_event),
        heartbeat,
        has_successful_mux,
        awaiting_mux,
        shutdown_event,
    )


def send(
    config: dict[str, Any],
    packets: Iterator[EncodedPacket],
    heartbeat,
    has_successful_mux,
    awaiting_mux,
    shutdown_event,
) -> None:
    """인코딩 패킷을 RTSP로 mux하고 성공 시 heartbeat를 갱신한다."""
    output_rtsp = config["output"]["rtsp"]
    url = output_rtsp["url"]
    transport = output_rtsp["transport"]
    container = None
    output_stream = None
    connected = False
    awaiting_keyframe = True

    try:
        for packet in packets:
            while not shutdown_event.is_set():
                if awaiting_keyframe and not packet.is_keyframe:
                    logger.debug("키프레임 대기 중 패킷 폐기: pts=%s", packet.pts)
                    break

                try:
                    if container is None:
                        container = av.open(
                            url,
                            mode="w",
                            format="rtsp",
                            options={
                                "rtsp_transport": transport,
                                "flush_packets": "1",
                            },
                            timeout=(5.0, 5.0),
                        )
                        logger.info("송출 RTSP 연결 시도")

                        output_stream = container.add_stream(packet.codec)
                        output_stream.width = packet.width
                        output_stream.height = packet.height
                        output_stream.time_base = packet.time_base

                    send_packet = av.Packet(packet.packet_data)
                    send_packet.stream = output_stream
                    send_packet.pts = packet.pts
                    # NVENC is configured with bf=0, so decode and display
                    # order are identical.  Supplying matching DTS prevents
                    # the muxer/receiver from inferring a reordered timeline.
                    send_packet.dts = packet.pts
                    send_packet.time_base = output_stream.time_base
                    container.mux(send_packet)

                    if not connected:
                        logger.info("송출 RTSP 연결 성공")
                        connected = True

                    heartbeat.value = time.monotonic()
                    has_successful_mux.value = True
                    awaiting_mux.value = False
                    awaiting_keyframe = False
                    break

                except Exception as error:
                    logger.error("송출 RTSP 연결 실패: %s", error)
                    connected = False
                    awaiting_keyframe = True
                    if container is not None:
                        container.close()
                    container = None
                    output_stream = None
                    shutdown_event.wait(1)
    finally:
        if container is not None:
            container.close()
