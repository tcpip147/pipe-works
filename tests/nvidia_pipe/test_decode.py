import sys
import unittest
from fractions import Fraction
from types import SimpleNamespace
from unittest import mock

from nvidia_pipe.decode import calculate_fps, decode
from nvidia_pipe.stream import ReceivedPacket


class FakeFrame:
    def __init__(self, pts, payload):
        self._pts = pts
        self.payload = payload

    def getPTS(self):
        return self._pts


class FakeDecoder:
    def __init__(self, frames):
        self.frames = frames
        self.pixel_format = SimpleNamespace(name="NV12")
        self.calls = []

    def GetPixelFormat(self):
        return self.pixel_format

    def Decode(self, packet_data):
        self.calls.append(packet_data)
        return self.frames


class FakeNvc:
    class OutputColorType:
        NATIVE = "native"
        RGB = "rgb"
        RGBP = "rgbp"

    class DisplayDecodeLatencyType:
        NATIVE = "native"


class DecodeTests(unittest.TestCase):
    def setUp(self):
        self.stream = SimpleNamespace(
            width=1280,
            height=720,
            time_base=Fraction(1, 90000),
            average_rate=Fraction(25, 1),
        )
        self.packet = ReceivedPacket(
            codec=SimpleNamespace(name="H264"),
            input_stream=self.stream,
            packet_data=SimpleNamespace(),
            bitstream_buffer=None,
        )

    def test_decode_preserves_metadata_for_each_frame(self):
        frames = [FakeFrame(10, "a"), FakeFrame(20, "b")]
        decoder = FakeDecoder(frames)
        nvc = SimpleNamespace(
            OutputColorType=FakeNvc.OutputColorType,
            DisplayDecodeLatencyType=FakeNvc.DisplayDecodeLatencyType,
            CreateDecoder=mock.Mock(return_value=decoder),
        )
        config = {"inference": {"gpuid": 1, "input_format": "rgb"}}

        with mock.patch.dict(sys.modules, {"PyNvVideoCodec": nvc}):
            result = list(decode(config, iter([self.packet])))

        self.assertEqual([frame.pts for frame in result], [10, 20])
        self.assertEqual(result[0].gpuid, 1)
        self.assertEqual(result[0].codec, "h264")
        self.assertEqual(result[0].width, 1280)
        self.assertEqual(result[0].height, 720)
        self.assertEqual(result[0].pixel_format, "NV12")
        self.assertEqual(result[0].time_base, Fraction(1, 90000))
        self.assertEqual(result[0].frame_rate, Fraction(25, 1))
        self.assertEqual(result[0].frame_data, frames[0])
        nvc.CreateDecoder.assert_called_once()
        self.assertEqual(nvc.CreateDecoder.call_args.kwargs["outputColorType"], "rgb")

    def test_decode_preserves_order_for_100_packets(self):
        packets = []
        frames = []
        for index in range(100):
            frame = FakeFrame(index, index)
            frames.append(frame)
            packets.append(
                ReceivedPacket(
                    codec=SimpleNamespace(name="H264"),
                    input_stream=self.stream,
                    packet_data=SimpleNamespace(index=index),
                    bitstream_buffer=None,
                )
            )

        class PerPacketDecoder(FakeDecoder):
            def Decode(self, packet_data):
                self.calls.append(packet_data)
                return [frames[packet_data.index]]

        decoder = PerPacketDecoder([])
        nvc = SimpleNamespace(
            OutputColorType=FakeNvc.OutputColorType,
            DisplayDecodeLatencyType=FakeNvc.DisplayDecodeLatencyType,
            CreateDecoder=mock.Mock(return_value=decoder),
        )
        config = {"inference": {"gpuid": 1, "input_format": "native"}}

        with mock.patch.dict(sys.modules, {"PyNvVideoCodec": nvc}):
            result = list(decode(config, iter(packets)))

        self.assertEqual(len(result), 100)
        self.assertEqual([frame.pts for frame in result], list(range(100)))

    def test_decode_supports_all_input_formats(self):
        for input_format, expected in (
            ("native", FakeNvc.OutputColorType.NATIVE),
            ("rgb", FakeNvc.OutputColorType.RGB),
            ("rgbp", FakeNvc.OutputColorType.RGBP),
        ):
            decoder = FakeDecoder([FakeFrame(1, "frame")])
            nvc = SimpleNamespace(
                OutputColorType=FakeNvc.OutputColorType,
                DisplayDecodeLatencyType=FakeNvc.DisplayDecodeLatencyType,
                CreateDecoder=mock.Mock(return_value=decoder),
            )
            config = {"inference": {"gpuid": 0, "input_format": input_format}}
            with mock.patch.dict(sys.modules, {"PyNvVideoCodec": nvc}):
                list(decode(config, iter([self.packet])))
            self.assertEqual(
                nvc.CreateDecoder.call_args.kwargs["outputColorType"], expected
            )

    def test_unsupported_input_format_raises(self):
        config = {"inference": {"gpuid": 0, "input_format": "yuv420"}}
        with mock.patch.dict(sys.modules, {"PyNvVideoCodec": FakeNvc}):
            with self.assertRaisesRegex(ValueError, "yuv420"):
                next(decode(config, iter([self.packet])))

    def test_calculate_fps_uses_median_positive_deltas(self):
        frames = [FakeFrame(0, None), FakeFrame(30, None), FakeFrame(70, None), FakeFrame(100, None)]
        self.assertAlmostEqual(calculate_fps(frames, Fraction(1, 30)), 1.0)

    def test_calculate_fps_returns_none_without_valid_deltas(self):
        self.assertIsNone(calculate_fps([FakeFrame(1, None)], Fraction(1, 90000)))
        self.assertIsNone(calculate_fps([FakeFrame(10, None), FakeFrame(10, None)], Fraction(1, 90000)))


if __name__ == "__main__":
    unittest.main()
