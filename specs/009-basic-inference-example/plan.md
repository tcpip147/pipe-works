# 구현 계획: 기본 추론 예제 시간 오버레이

## 기술 맥락

PyNvVideoCodec의 GPU 디코드 프레임은 DLPack을 통해 PyTorch Tensor로 연결된다. 기본 예제는 NV12 프레임의 Y 평면에 비트맵 글꼴을 기록하고, 수정된 GPU 프레임을 `set_frame_data`로 반환한다.

## 설계

`on_frame`은 호출마다 현재 지역 시간을 `yyyy-mm-dd hh24:mi:ss` 형식으로 만든다. NV12의 휘도 평면 우측 상단에 흰색 비트맵 글꼴을 그린다. GPU 텐서의 슬라이스만 갱신하므로 전체 프레임의 CPU 복사는 수행하지 않는다. NV12가 아니거나 DLPack이 2차원 휘도 평면을 노출하지 않으면 명확한 오류를 반환한다.

## 파일 변경

- `examples/inference.py`: 시간 문자열 생성, NV12 GPU 오버레이, `set_frame_data` 호출을 구현한다.
- `tests/test_inference_example.py`: 시간 표시, `infer` 플래그 무관 동작, NV12 형식 검증을 확인한다.

## 검증

`PYTHONPATH=src python -m unittest tests.test_inference_example -v`와 전체 단위 테스트를 실행한다. 실제 NV12 CUDA 프레임 검증은 NVIDIA GPU 환경에서 RTSP 입력으로 별도 수행한다.
