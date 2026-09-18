import sys
import unittest
from fractions import Fraction
from types import SimpleNamespace
from unittest import mock

from nvidia_pipe.encode import encode
from nvidia_pipe.stream import GpuFrame


class FakeEncoder:
    def __init__(self):
        self.inputs = []

    def Encode(self, frame_data):
        self.inputs.append(frame_data)
        return [{"timestamp": len(self.inputs), "payload": frame_data}]

    def EndEncode(self):
        return [{"timestamp": 999, "payload": "flush"}]


class FakeNvc:
    def __init__(self, encoder):
        self.encoder = encoder

    def CreateEncoder(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self.encoder


def frame(index, frame_rate=Fraction(25, 1)):
    return GpuFrame(
        0,
        "h264",
        1920,
        1080,
        "NV12",
        Fraction(1, 90000),
        frame_rate,
        index,
        f"frame-{index}",
    )


class EncodeTests(unittest.TestCase):
    def test_encodes_100_frames_in_order_and_preserves_metadata(self):
        encoder = FakeEncoder()
        nvc = FakeNvc(encoder)
        with mock.patch.dict(sys.modules, {"PyNvVideoCodec": nvc}):
            result = list(encode(iter(frame(i) for i in range(100))))

        self.assertEqual(len(result), 101)
        self.assertEqual([packet.pts for packet in result[:100]], list(range(1, 101)))
        self.assertEqual(result[0].codec, "h264")
        self.assertEqual(result[0].width, 1920)
        self.assertEqual(result[0].height, 1080)
        self.assertEqual(result[0].time_base, Fraction(1, 25))
        self.assertEqual(result[0].packet_data["payload"], "frame-0")
        self.assertEqual(encoder.inputs, [f"frame-{i}" for i in range(100)])
        self.assertEqual(nvc.kwargs["gpu_id"], 0)
        self.assertEqual(nvc.kwargs["codec"], "h264")
        self.assertEqual(nvc.kwargs["bf"], 0)
        self.assertEqual(nvc.kwargs["fps"], 25)
        self.assertEqual(nvc.kwargs["gop"], 25)
        self.assertEqual(nvc.kwargs["idrperiod"], 25)
        self.assertEqual(nvc.args[:3], (1920, 1080, "NV12"))

    def test_uses_nearest_whole_fps_for_fractional_source_rates(self):
        encoder = FakeEncoder()
        nvc = FakeNvc(encoder)
        with mock.patch.dict(sys.modules, {"PyNvVideoCodec": nvc}):
            result = list(encode(iter([frame(1, Fraction(30000, 1001))])))
        self.assertEqual(nvc.kwargs["fps"], 30)
        self.assertEqual(nvc.kwargs["idrperiod"], 30)
        self.assertEqual(result[0].time_base, Fraction(1, 30))

    def test_multiple_packets_per_frame_keep_output_order(self):
        class MultiPacketEncoder(FakeEncoder):
            def Encode(self, frame_data):
                self.inputs.append(frame_data)
                index = len(self.inputs)
                return [
                    {"timestamp": index * 2 - 1, "payload": f"{frame_data}-a"},
                    {"timestamp": index * 2, "payload": f"{frame_data}-b"},
                ]

            def EndEncode(self):
                return []

        encoder = MultiPacketEncoder()
        nvc = FakeNvc(encoder)
        with mock.patch.dict(sys.modules, {"PyNvVideoCodec": nvc}):
            result = list(encode(iter([frame(1), frame(2)])))
        self.assertEqual(
            [packet.packet_data["payload"] for packet in result],
            ["frame-1-a", "frame-1-b", "frame-2-a", "frame-2-b"],
        )

    def test_end_encode_packets_are_emitted(self):
        encoder = FakeEncoder()
        nvc = FakeNvc(encoder)
        with mock.patch.dict(sys.modules, {"PyNvVideoCodec": nvc}):
            result = list(encode(iter([frame(1)])))
        self.assertEqual(result[-1].pts, 999)
        self.assertEqual(result[-1].packet_data["payload"], "flush")


if __name__ == "__main__":
    unittest.main()
