# 구현 계획: NVDEC 영상 디코딩

**기능**: `002-nvdec-decode`  
**명세**: [spec.md](spec.md)

## 기술 맥락

- Python 3.11, PyNvVideoCodec, PyTorch 데이터 모델
- 입력: `ReceivedPacket`
- 출력: `GpuFrame`
- 기존 `src/nvidia_pipe/decode.py`의 `decode` 및 `calculate_fps`를 기준으로 한다.

## 설계

1. 첫 패킷에서 GPU 번호, 색상 형식, 코덱, 시간 기준으로 디코더를 한 번 초기화한다.
2. 이후 패킷은 동일 디코더에 전달하고 반환된 프레임마다 `GpuFrame`을 생성한다.
3. FPS는 유효한 증가 PTS 간격만 수집해 중간값으로 계산한다.
4. 외부 라이브러리는 테스트에서 모의 객체로 대체한다.

## 파일 변경

- `src/nvidia_pipe/decode.py`: 디코딩·FPS 동작과 오류 메시지 정합화
- `tests/nvidia_pipe/test_decode.py`: 형식 선택, 메타데이터, FPS, 오류 검증
- `specs/002-nvdec-decode/*`: 명세 산출물

## 검증

`PYTHONPATH=src` 환경에서 `python -m unittest discover -s tests -t . -p "test_*.py"`를 실행한다. 실제 GPU/RTSP 통합 검증은 장비가 있는 환경에서 별도로 수행한다.
