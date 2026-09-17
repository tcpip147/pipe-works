"""GPU-only YOLO car detection example for an NV12 video pipeline."""

from __future__ import annotations

from typing import Any

import torch
from torch.nn import functional as F

from nvidia_pipe.stream import GpuFrame

_CAR_CLASS_ID = 2  # COCO "car"
_DEFAULT_CONFIDENCE = 0.25
_DEFAULT_MODEL = "yolo11n.pt"
_GREEN_YUV = (150, 43, 21)
_BOX_THICKNESS = 3

_model: Any | None = None
_model_path: str | None = None
_last_car_boxes: torch.Tensor | None = None


def _parameters(parameters: dict | None) -> tuple[str, float]:
    parameters = parameters if isinstance(parameters, dict) else {}
    model_path = parameters.get("model", _DEFAULT_MODEL)
    model_path = model_path if isinstance(model_path, str) and model_path else _DEFAULT_MODEL
    try:
        confidence = float(parameters.get("confidence", _DEFAULT_CONFIDENCE))
    except (TypeError, ValueError):
        confidence = _DEFAULT_CONFIDENCE
    return model_path, min(1.0, max(0.0, confidence))


def _nv12_to_rgb(nv12: torch.Tensor, height: int, width: int) -> torch.Tensor:
    """Convert a two-plane NV12 tensor to normalized RGB BCHW without a CPU copy."""
    y = nv12[:height, :width].to(torch.float32)
    uv = nv12[height : height + height // 2, :width].reshape(height // 2, width // 2, 2)
    u = F.interpolate(uv[..., 0][None, None].to(torch.float32), size=(height, width), mode="nearest")[0, 0]
    v = F.interpolate(uv[..., 1][None, None].to(torch.float32), size=(height, width), mode="nearest")[0, 0]
    y = (y - 16.0).clamp_min_(0.0) * (1.0 / 219.0)
    u = (u - 128.0) * (1.0 / 224.0)
    v = (v - 128.0) * (1.0 / 224.0)
    return torch.stack((y + 1.402 * v, y - 0.344136 * u - 0.714136 * v, y + 1.772 * u)).clamp_(0, 1)[None]


def _pad_to_yolo_stride(rgb: torch.Tensor) -> torch.Tensor:
    """Pad only the right and bottom edges so a tensor input meets YOLO's stride."""
    height, width = rgb.shape[-2:]
    return F.pad(rgb, (0, (-width) % 32, 0, (-height) % 32))


def _get_model(model_path: str, gpuid: int) -> Any:
    global _model, _model_path
    if _model is None or _model_path != model_path:
        from ultralytics import YOLO

        _model = YOLO(model_path)
        _model_path = model_path
    return _model.to(f"cuda:{gpuid}")


def _detect_cars(frame: GpuFrame, model_path: str, confidence: float) -> torch.Tensor:
    nv12 = torch.from_dlpack(frame.frame_data)
    if frame.pixel_format.upper() != "NV12":
        raise ValueError("The YOLO car example requires NV12 input frames")
    if nv12.ndim != 2 or frame.height % 2 or frame.width % 2:
        raise ValueError("NV12 frame data must expose even-sized two-dimensional planes")
    rgb = _nv12_to_rgb(nv12, frame.height, frame.width)
    result = _get_model(model_path, frame.gpuid)(
        _pad_to_yolo_stride(rgb), conf=confidence, verbose=False
    )[0]
    boxes = result.boxes
    if boxes is None or boxes.xyxy.numel() == 0:
        return rgb.new_empty((0, 4))
    return boxes.xyxy[boxes.cls.to(torch.int64) == _CAR_CLASS_ID]


def _draw_car_boxes_nv12(frame: GpuFrame, boxes: torch.Tensor) -> None:
    """Draw green box outlines directly into the original NV12 buffer."""
    nv12 = torch.from_dlpack(frame.frame_data)
    if boxes.numel() == 0:
        frame.set_frame_data(nv12)
        return
    boxes = boxes.to(device=nv12.device, dtype=torch.int64)
    x1, y1, x2, y2 = boxes.unbind(1)
    x1 = x1.clamp(0, frame.width - 1)[:, None, None]
    x2 = x2.clamp(0, frame.width - 1)[:, None, None]
    y1 = y1.clamp(0, frame.height - 1)[:, None, None]
    y2 = y2.clamp(0, frame.height - 1)[:, None, None]
    xs = torch.arange(frame.width, device=nv12.device)[None, None, :]
    ys = torch.arange(frame.height, device=nv12.device)[None, :, None]
    inside_x = (xs >= x1) & (xs <= x2)
    inside_y = (ys >= y1) & (ys <= y2)
    edge_x = ((xs - x1).abs() < _BOX_THICKNESS) | ((xs - x2).abs() < _BOX_THICKNESS)
    edge_y = ((ys - y1).abs() < _BOX_THICKNESS) | ((ys - y2).abs() < _BOX_THICKNESS)
    mask = (inside_x & inside_y & (edge_x | edge_y)).any(dim=0)
    nv12[: frame.height, : frame.width][mask] = _GREEN_YUV[0]
    chroma_mask = F.max_pool2d(mask[None, None].to(torch.float32), 2, 2)[0, 0].bool()
    chroma = nv12[frame.height : frame.height + frame.height // 2, : frame.width]
    chroma[:, 0::2][chroma_mask] = _GREEN_YUV[1]
    chroma[:, 1::2][chroma_mask] = _GREEN_YUV[2]
    frame.set_frame_data(nv12)


def on_frame(frame: GpuFrame, infer: bool, parameters: dict | None = None) -> GpuFrame:
    """Run YOLO on inference frames and overlay the latest detected cars in green."""
    global _last_car_boxes
    model_path, confidence = _parameters(parameters)
    if infer or _last_car_boxes is None:
        _last_car_boxes = _detect_cars(frame, model_path, confidence)
    _draw_car_boxes_nv12(frame, _last_car_boxes)
    return frame
