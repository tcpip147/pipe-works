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
    width = 64
    height = 32
    gpuid = 0

    def __init__(self):
        self.frame_data = torch.zeros((48, 64), dtype=torch.uint8)
        self.replacement = None

    def set_frame_data(self, frame_data):
        self.replacement = frame_data
        self.frame_data = frame_data


class InferenceExampleTests(unittest.TestCase):
    def setUp(self):
        inference._last_car_boxes = None

    def test_on_frame_draws_green_box_and_replaces_frame_data(self):
        frame = FakeFrame()
        boxes = torch.tensor([[10.0, 8.0, 30.0, 20.0]])
        with mock.patch.object(inference, "_detect_cars", return_value=boxes):
            result = inference.on_frame(frame, infer=True)

        self.assertIs(result, frame)
        self.assertIs(frame.replacement, frame.frame_data)
        self.assertTrue(torch.any(frame.frame_data[: frame.height] == 150))
        self.assertTrue(torch.any(frame.frame_data[frame.height :, 0::2] == 43))
        self.assertTrue(torch.any(frame.frame_data[frame.height :, 1::2] == 21))

    def test_skipped_inference_reuses_the_last_gpu_boxes(self):
        boxes = torch.tensor([[10.0, 8.0, 30.0, 20.0]])
        with mock.patch.object(inference, "_detect_cars", return_value=boxes) as detect:
            inference.on_frame(FakeFrame(), infer=True)
            later = FakeFrame()
            inference.on_frame(later, infer=False)

        detect.assert_called_once()
        self.assertTrue(torch.any(later.frame_data[: later.height] == 150))

    def test_non_nv12_frame_is_rejected_before_model_execution(self):
        frame = FakeFrame()
        frame.pixel_format = "RGB"
        with self.assertRaisesRegex(ValueError, "NV12"):
            inference._detect_cars(frame, "test.pt", 0.25)

    def test_detect_cars_keeps_only_coco_car_class(self):
        frame = FakeFrame()
        result = mock.Mock()
        result.boxes.xyxy = torch.tensor([[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]])
        result.boxes.cls = torch.tensor([2.0, 0.0])
        model = mock.Mock(return_value=[result])

        with mock.patch.object(inference, "_get_model", return_value=model):
            cars = inference._detect_cars(frame, "test.pt", 0.5)

        self.assertTrue(torch.equal(cars, result.boxes.xyxy[:1]))
        model.assert_called_once()

    def test_yolo_input_is_padded_to_its_stride_without_resizing(self):
        rgb = torch.zeros((1, 3, 1080, 1920))

        padded = inference._pad_to_yolo_stride(rgb)

        self.assertEqual(padded.shape, (1, 3, 1088, 1920))


if __name__ == "__main__":
    unittest.main()
