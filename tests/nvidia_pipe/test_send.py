import threading
import unittest
from fractions import Fraction
from types import SimpleNamespace
from unittest import mock

from nvidia_pipe.send import is_idr_keyframe, send, send_worker
from nvidia_pipe.stream import EncodedPacket


class FakeContainer:
    def __init__(self):
        self.muxed = []
        self.closed = False
        self.stream = SimpleNamespace(time_base=None, width=None, height=None)

    def add_stream(self, codec):
        self.codec = codec
        return self.stream

    def mux(self, packet):
        self.muxed.append(packet)

    def close(self):
        self.closed = True


class SendTests(unittest.TestCase):
    config = {"output": {"rtsp": {"url": "rtsp://example/out", "transport": "tcp"}}}

    def test_mux_updates_heartbeat_and_logs_success_after_mux(self):
        container = FakeContainer()
        heartbeat = SimpleNamespace(value=0)
        shutdown = threading.Event()
        packet = EncodedPacket("h264", 640, 360, Fraction(1, 90000), 7, b"data", True)

        with mock.patch("nvidia_pipe.send.av.open", return_value=container), mock.patch(
            "nvidia_pipe.send.av.Packet", return_value=SimpleNamespace()
        ), self.assertLogs("nvidia_pipe.send", level="INFO") as logs:
            send(self.config, iter([packet]), heartbeat, shutdown)

        self.assertEqual(len(container.muxed), 1)
        self.assertNotEqual(heartbeat.value, 0)
        self.assertTrue(any("?깃났" in message or "성공" in message for message in logs.output))
        self.assertTrue(container.closed)

    def test_muxes_100_packets_in_order(self):
        container = FakeContainer()
        heartbeat = SimpleNamespace(value=0)
        shutdown = threading.Event()
        packets = [EncodedPacket("h264", 640, 360, Fraction(1, 90000), i, bytes([i]), True) for i in range(100)]

        with mock.patch("nvidia_pipe.send.av.open", return_value=container), mock.patch(
            "nvidia_pipe.send.av.Packet", side_effect=lambda data: SimpleNamespace(data=data)
        ):
            send(self.config, iter(packets), heartbeat, shutdown)

        self.assertEqual([item.data for item in container.muxed], [bytes([i]) for i in range(100)])

    def test_waits_for_keyframe_before_opening_and_muxing(self):
        container = FakeContainer()
        heartbeat = SimpleNamespace(value=0)
        shutdown = threading.Event()
        packets = iter([
            EncodedPacket("h264", 640, 360, Fraction(1, 90000), 1, b"p-frame", False),
            EncodedPacket("h264", 640, 360, Fraction(1, 90000), 2, b"idr", True),
        ])

        with mock.patch("nvidia_pipe.send.av.open", return_value=container) as open_mock, mock.patch(
            "nvidia_pipe.send.av.Packet", side_effect=lambda data: SimpleNamespace(data=data)
        ):
            send(self.config, packets, heartbeat, shutdown)

        open_mock.assert_called_once()
        self.assertEqual([item.data for item in container.muxed], [b"idr"])

    def test_send_failure_discards_intervening_packets_until_next_keyframe(self):
        first = FakeContainer()
        recovered = FakeContainer()
        heartbeat = SimpleNamespace(value=0)
        shutdown = threading.Event()
        packets = iter([
            EncodedPacket("h264", 640, 360, Fraction(1, 90000), 1, b"idr-1", True),
            EncodedPacket("h264", 640, 360, Fraction(1, 90000), 2, b"p-frame", False),
            EncodedPacket("h264", 640, 360, Fraction(1, 90000), 3, b"idr-2", True),
        ])

        original_mux = first.mux

        def fail_after_first_packet(packet):
            if first.muxed:
                raise OSError("connection lost")
            original_mux(packet)

        first.mux = fail_after_first_packet
        with mock.patch("nvidia_pipe.send.av.open", side_effect=[first, recovered]) as open_mock, mock.patch(
            "nvidia_pipe.send.av.Packet", side_effect=lambda data: SimpleNamespace(data=data)
        ), mock.patch.object(shutdown, "wait", return_value=False):
            send(self.config, packets, heartbeat, shutdown)

        self.assertEqual(open_mock.call_count, 2)
        self.assertEqual([item.data for item in first.muxed], [b"idr-1"])
        self.assertEqual([item.data for item in recovered.muxed], [b"idr-2"])

    def test_idr_keyframe_detection_supports_h264_and_hevc_annex_b(self):
        self.assertTrue(is_idr_keyframe("h264", b"\x00\x00\x00\x01\x65\x00"))
        self.assertFalse(is_idr_keyframe("h264", b"\x00\x00\x01\x41\x00"))
        self.assertTrue(is_idr_keyframe("hevc", b"\x00\x00\x01\x26\x01"))
        self.assertFalse(is_idr_keyframe("hevc", b"\x00\x00\x01\x02\x01"))
        self.assertFalse(is_idr_keyframe("hevc", b"\x00\x00\x01\x2A\x01"))

    def test_worker_configures_logging_with_yaml_pipeline_name(self):
        config = {"name": "camera-a"}
        packet_queue = mock.Mock()
        heartbeat = mock.Mock()
        shutdown = mock.Mock()

        with mock.patch("nvidia_pipe.cli.configure_pipeline_logging") as configure_logging, mock.patch(
            "nvidia_pipe.send.send"
        ) as send_mock:
            send_worker(packet_queue, config, heartbeat, shutdown)

        configure_logging.assert_called_once_with("camera-a")
        send_mock.assert_called_once()

    def test_submit_drops_oldest_packet_when_queue_is_full(self):
        sender = __import__("nvidia_pipe.send", fromlist=["Sender"]).Sender(self.config, queue_size=1)
        sender._queue = __import__("queue").Queue(maxsize=1)
        first = EncodedPacket("h264", 1, 1, Fraction(1, 1), 1, b"first")
        latest = EncodedPacket("h264", 1, 1, Fraction(1, 1), 2, b"latest")
        sender.submit(first)
        sender.submit(latest)
        self.assertEqual(sender._queue.get_nowait().pts, 2)

    def test_stop_process_uses_join_then_terminate_then_kill(self):
        from nvidia_pipe.send import Sender

        sender = Sender(self.config)
        process = mock.Mock()
        process.is_alive.side_effect = [True, True, True, False]
        process.join = mock.Mock()
        sender._process = process
        worker_stop = mock.Mock()
        sender._worker_stop = worker_stop
        sender._stop_process()
        worker_stop.set.assert_called_once()
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertIsNone(sender._process)

    def test_monitor_restarts_stalled_sender_only(self):
        from nvidia_pipe.send import Sender

        sender = Sender(self.config, heartbeat_timeout=10)
        sender._process = mock.Mock()
        sender._process.is_alive.return_value = True
        sender._heartbeat.value = 0
        sender._monitor_stop.wait = mock.Mock(side_effect=[False, True])
        with mock.patch("nvidia_pipe.send.time.monotonic", return_value=20), mock.patch.object(
            sender, "_stop_process"
        ) as stop, mock.patch.object(sender, "_start_process") as start:
            sender._monitor_loop()
        stop.assert_called_once()
        start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
