import importlib.util
from pathlib import Path
import unittest
from unittest import mock

import torch


EXAMPLE_PATH = Path(__file__).parents[1] / "examples" / "inference.py"
SPEC = importlib.util.spec_from_file_location("basic_inference_example", EXAMPLE_PATH)
assert SPEC is not None and SPEC.loader is not None
inference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inference)


class FakeFrame:
    pixel_format = "NV12"
    width = 256
    height = 64

    def __init__(self):
        self.frame_data = torch.zeros((96, 256), dtype=torch.uint8)
        self.replacement = None

    def set_frame_data(self, frame_data):
        self.replacement = frame_data
        self.frame_data = frame_data


class InferenceExampleTests(unittest.TestCase):
    def setUp(self):
        inference._last_inference_result = None

    def test_on_frame_draws_current_timestamp_and_replaces_frame_data(self):
        frame = FakeFrame()
        now = mock.Mock()
        now.strftime.return_value = "2026-09-15 12:34:56"

        with mock.patch.object(inference, "datetime") as datetime_mock:
            datetime_mock.now.return_value = now
            result = inference.on_frame(frame, infer=True)

        self.assertIs(result, frame)
        self.assertIs(frame.replacement, frame.frame_data)
        self.assertGreater(torch.count_nonzero(frame.frame_data[: frame.height]).item(), 0)
        self.assertGreater(torch.count_nonzero(frame.frame_data[frame.height :]).item(), 0)

    def test_on_frame_reuses_last_inference_result_when_interval_skips_model_work(self):
        frame = FakeFrame()
        first_now = mock.Mock()
        first_now.strftime.return_value = "2026-09-15 12:34:56"
        later_now = mock.Mock()
        later_now.strftime.return_value = "2026-09-15 12:35:00"

        with mock.patch.object(inference, "datetime") as datetime_mock:
            datetime_mock.now.return_value = first_now
            inference.on_frame(FakeFrame(), infer=True)
            datetime_mock.now.return_value = later_now
            inference.on_frame(frame, infer=False)

        self.assertGreater(torch.count_nonzero(frame.frame_data[: frame.height]).item(), 0)
        first_now.strftime.assert_called_once_with("%Y-%m-%d %H:%M:%S")
        later_now.strftime.assert_not_called()

    def test_timestamp_overlay_rejects_non_nv12_frames(self):
        frame = FakeFrame()
        frame.pixel_format = "RGB"

        with self.assertRaisesRegex(ValueError, "NV12"):
            inference.on_frame(frame, infer=True)

    def test_timestamp_overlay_uses_parameterized_yuv_and_font_size(self):
        timestamp = "2026-09-15 12:34:56"
        small = FakeFrame()
        large = FakeFrame()

        inference._draw_timestamp_nv12(
            small, timestamp, {"font-size": 7, "yuv": [101, 102, 103]}
        )
        inference._draw_timestamp_nv12(
            large, timestamp, {"font-size": 28, "yuv": [101, 102, 103]}
        )

        self.assertTrue(torch.any(small.frame_data == 101))
        self.assertTrue(torch.any(small.frame_data == 102))
        self.assertTrue(torch.any(small.frame_data == 103))
        self.assertGreater(
            torch.count_nonzero(large.frame_data[: large.height]).item(),
            torch.count_nonzero(small.frame_data[: small.height]).item(),
        )

    def test_timestamp_overlay_falls_back_for_invalid_parameters(self):
        frame = FakeFrame()

        inference._draw_timestamp_nv12(
            frame, "2026-09-15 12:34:56", {"font-size": "bad", "yuv": [1, 2]}
        )

        self.assertTrue(torch.any(frame.frame_data == 150))
        self.assertTrue(torch.any(frame.frame_data == 43))
        self.assertTrue(torch.any(frame.frame_data == 21))


if __name__ == "__main__":
    unittest.main()
