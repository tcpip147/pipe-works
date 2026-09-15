from dataclasses import dataclass
from av.video.stream import VideoStream
from fractions import Fraction
from torch.nn import functional as F

import torch


@dataclass(slots=True)
class ReceivedPacket:
    codec: object
    input_stream: VideoStream
    packet_data: object
    bitstream_buffer: object


@dataclass(slots=True)
class GpuFrame:
    __gpuid: int
    __codec: str
    __width: int
    __height: int
    __pixel_format: str
    __time_base: Fraction
    __frame_rate: Fraction | None
    __pts: object
    __frame_data: object

    @property
    def gpuid(self) -> int:
        return self.__gpuid

    @property
    def codec(self) -> str:
        return self.__codec

    @property
    def width(self) -> int:
        return self.__width

    @property
    def height(self) -> int:
        return self.__height

    @property
    def pixel_format(self) -> str:
        return self.__pixel_format

    @property
    def time_base(self) -> Fraction:
        return self.__time_base

    @property
    def frame_rate(self) -> Fraction | None:
        return self.__frame_rate

    @property
    def pts(self) -> object:
        return self.__pts

    @property
    def frame_data(self) -> object:
        return self.__frame_data

    def set_frame_data(self, frame_data: object) -> None:
        self.__frame_data = frame_data


@dataclass(slots=True)
class EncodedPacket:
    codec: str
    width: int
    height: int
    time_base: Fraction
    pts: object
    packet_data: object
    is_keyframe: bool = False
