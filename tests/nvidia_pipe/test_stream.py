import unittest
from fractions import Fraction
from types import SimpleNamespace
from nvidia_pipe.stream import EncodedPacket, GpuFrame, ReceivedPacket

class StreamContractTests(unittest.TestCase):
    def test_all_data_contract_fields_are_available(self):
        received = ReceivedPacket("h264", SimpleNamespace(), "packet", "buffer")
        gpu = GpuFrame(0, "h264", 1, 1, "NV12", Fraction(1, 1), Fraction(25, 1), 2, "frame")
        encoded = EncodedPacket("h264", 1, 1, Fraction(1, 1), 3, b"encoded")
        self.assertEqual(received.bitstream_buffer, "buffer")
        self.assertEqual((gpu.gpuid, gpu.codec, gpu.pts, gpu.frame_data), (0, "h264", 2, "frame"))
        self.assertEqual(gpu.frame_rate, Fraction(25, 1))
        self.assertEqual((encoded.codec, encoded.pts, encoded.packet_data), ("h264", 3, b"encoded"))

    def test_gpu_frame_exposes_an_optional_inference_result(self):
        gpu = GpuFrame(0, "h264", 1, 1, "NV12", Fraction(1, 1), None, 2, "frame")

        self.assertIsNone(gpu.inference_result)
        result = object()
        gpu.set_inference_result(result)
        self.assertIs(gpu.inference_result, result)

if __name__ == "__main__":
    unittest.main()
