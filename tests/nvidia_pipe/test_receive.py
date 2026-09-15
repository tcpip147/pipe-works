import ctypes
from types import SimpleNamespace
import sys
import unittest
from unittest import mock

from nvidia_pipe.receive import receive


class FakePacket:
    def __init__(self, *, pts=100, dts=90, duration=40, keyframe=True, data=b"abc"):
        self.pts = pts
        self.dts = dts
        self.duration = duration
        self.is_keyframe = keyframe
        self._data = data

    def __bytes__(self):
        return self._data


class FakeContainer:
    def __init__(self, codec_name="h264", packets=None):
        stream = SimpleNamespace(
            codec_context=SimpleNamespace(name=codec_name),
            width=1920,
            height=1080,
            average_rate="30",
            time_base=SimpleNamespace(numerator=1, denominator=90000),
        )
        self.streams = SimpleNamespace(video=[stream])
        self._packets = packets or [FakePacket()]
        self.closed = False

    def demux(self, video):
        self.assert_video_index = video
        yield from self._packets

    def close(self):
        self.closed = True


class FakeNvc:
    class cudaVideoCodec:
        H264 = "h264"
        HEVC = "hevc"

    class PacketData:
        pass


class ReceiveTests(unittest.TestCase):
    config = {"input": {"rtsp": {"url": "rtsp://example/live", "transport": "tcp"}}}

    def nvc_module(self):
        return mock.patch.dict(sys.modules, {"PyNvVideoCodec": FakeNvc})

    def test_supported_packet_preserves_metadata_and_buffer_ownership(self):
        container = FakeContainer()

        with self.nvc_module(), mock.patch(
            "nvidia_pipe.receive.av.open", return_value=container
        ):
            received = next(receive(self.config))

        self.assertEqual(received.codec, FakeNvc.cudaVideoCodec.H264)
        self.assertEqual(received.packet_data.pts, 100)
        self.assertEqual(received.packet_data.dts, 90)
        self.assertEqual(received.packet_data.duration, 40)
        self.assertTrue(received.packet_data.key)
        self.assertEqual(received.packet_data.bsl, 3)
        self.assertEqual(received.packet_data.bsl_data, ctypes.addressof(received.bitstream_buffer))
        self.assertEqual(received.bitstream_buffer.raw[:3], b"abc")

    def test_connection_error_waits_then_reconnects(self):
        container = FakeContainer()

        with self.nvc_module(), mock.patch(
            "nvidia_pipe.receive.av.open", side_effect=[OSError("offline"), container]
        ) as open_mock, mock.patch("nvidia_pipe.receive.time.sleep") as sleep_mock:
            received = next(receive(self.config))

        self.assertEqual(open_mock.call_count, 2)
        sleep_mock.assert_called_once_with(3)
        self.assertEqual(received.packet_data.pts, 100)

    def test_negative_pts_difference_is_aggregated_and_sets_duration_to_zero(self):
        container = FakeContainer(
            packets=[
                FakePacket(pts=100, dts=90, duration=40),
                FakePacket(pts=80, dts=70, duration=40),
                FakePacket(pts=60, dts=50, duration=40),
            ]
        )

        with self.nvc_module(), mock.patch(
            "nvidia_pipe.receive.av.open", return_value=container
        ), mock.patch(
            "nvidia_pipe.receive.time.monotonic", side_effect=[0, 1, 2, 5]
        ), self.assertLogs("nvidia_pipe.receive", level="WARNING") as logs:
            packets = receive(self.config)
            next(packets)
            received = next(packets)
            next(packets)

        self.assertEqual(received.packet_data.duration, 0)
        summaries = [message for message in logs.output if "시간 순서 이상 프레임" in message]
        self.assertEqual(len(summaries), 1)
        self.assertIn("2건", summaries[0])

    def test_unsupported_codec_is_logged_and_raised_without_retry(self):
        container = FakeContainer(codec_name="vp9")

        with self.nvc_module(), mock.patch(
            "nvidia_pipe.receive.av.open", return_value=container
        ) as open_mock, self.assertLogs("nvidia_pipe.receive", level="ERROR") as logs:
            with self.assertRaisesRegex(ValueError, "vp9"):
                next(receive(self.config))

        self.assertEqual(open_mock.call_count, 1)
        self.assertTrue(container.closed)
        self.assertTrue(any("vp9" in message for message in logs.output))


if __name__ == "__main__":
    unittest.main()
