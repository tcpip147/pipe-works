# 구현 계획: NVENC 영상 인코딩

**기능**: `003-nvenc-encode`  
**명세**: [spec.md](spec.md)

## 기술 맥락

Python 3.11과 PyNvVideoCodec을 사용하며, `GpuFrame`을 입력으로 받아 `EncodedPacket`을 반환한다.

## 설계

첫 프레임에서 인코더를 초기화하고 이후 프레임을 순차적으로 `Encode`에 전달한다. 입력 반복자가 종료되면 `EndEncode`를 호출해 잔여 패킷을 배출한다. 모든 출력은 입력 프레임의 코덱·해상도·시간 기준과 패킷 타임스탬프를 포함한다. 송신 연결은 H.264/H.265 Annex-B IDR 키프레임을 식별하고, 최초 연결 및 오류 복구 후에는 첫 IDR 키프레임까지 패킷을 폐기한다.

## 파일 변경

- `src/nvidia_pipe/encode.py`: 반환 타입과 인코딩 계약을 명확히 한다.
- `tests/nvidia_pipe/test_encode.py`: 인코더 초기화, 순서, 종료 패킷, 메타데이터를 검증한다.
- `src/nvidia_pipe/stream.py`: 송신 복구에 필요한 키프레임 여부를 패킷 계약에 추가한다.
- `src/nvidia_pipe/cli.py`: CPU 송신용 패킷 변환 시 IDR 키프레임 여부를 판별한다.
- `src/nvidia_pipe/send.py`: 재연결 뒤 키프레임부터 mux를 재개한다.
- `tests/nvidia_pipe/test_send.py`: 키프레임 대기 및 H.264/H.265 IDR 판별을 검증한다.

## 검증

`PYTHONPATH=src`에서 전체 unittest와 Python 문법 검사를 실행한다. 실제 GPU 검증은 PyNvVideoCodec과 NVIDIA 드라이버가 설치된 환경에서 별도 수행한다.
