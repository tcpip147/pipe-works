from nvidia_pipe.stream import GpuFrame
from datetime import datetime
import torch

_GLYPHS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "-": ("000", "000", "111", "000", "000"),
    ":": ("000", "010", "000", "010", "000"),
    " ": ("000", "000", "000", "000", "000"),
}

_GREEN_Y = 150
_GREEN_U = 43
_GREEN_V = 21
_last_inference_result: str | None = None


def _draw_timestamp_nv12(frame: GpuFrame, timestamp: str) -> None:
    """Draw a timestamp on the NV12 luma plane without copying the frame to CPU."""
    if frame.pixel_format.upper() != "NV12":
        raise ValueError("The basic timestamp example requires NV12 input frames")

    nv12 = torch.from_dlpack(frame.frame_data)
    if (
        nv12.ndim != 2
        or frame.height % 2
        or frame.width % 2
        or nv12.shape[0] < frame.height + frame.height // 2
        or nv12.shape[1] < frame.width
    ):
        raise ValueError("NV12 frame data must expose two-dimensional luma and chroma planes")

    glyph_width = 3
    glyph_spacing = 1
    margin = 8
    scale = max(1, min(4, (frame.width - 2 * margin) // (len(timestamp) * 4)))
    text_width = (
        len(timestamp) * (glyph_width + glyph_spacing) * scale - glyph_spacing * scale
    )
    x = max(margin, frame.width - margin - text_width)
    y = margin
    luma = nv12[: frame.height, : frame.width]

    for character in timestamp:
        for row, bits in enumerate(_GLYPHS[character]):
            for column, bit in enumerate(bits):
                if bit == "1":
                    y_start = y + row * scale
                    y_end = y + (row + 1) * scale
                    x_start = x + column * scale
                    x_end = x + (column + 1) * scale
                    luma[y_start:y_end, x_start:x_end] = _GREEN_Y

                    chroma_y_start = frame.height + y_start // 2
                    chroma_y_end = frame.height + (y_end + 1) // 2
                    chroma_x_start = (x_start // 2) * 2
                    chroma_x_end = ((x_end + 1) // 2) * 2
                    nv12[chroma_y_start:chroma_y_end, chroma_x_start:chroma_x_end:2] = _GREEN_U
                    nv12[chroma_y_start:chroma_y_end, chroma_x_start + 1:chroma_x_end:2] = _GREEN_V
        x += (glyph_width + glyph_spacing) * scale

    frame.set_frame_data(nv12)


def on_frame(frame: GpuFrame, infer: bool) -> GpuFrame:
    global _last_inference_result

    if infer or _last_inference_result is None:
        _last_inference_result = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _draw_timestamp_nv12(frame, _last_inference_result)
    return frame
