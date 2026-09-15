# 빠른 검증 안내: RTSP 영상 수신

## 사전 조건

- Python 3.11.9 가상 환경이 준비되어 있어야 한다.
- NVIDIA GPU, CUDA 런타임, PyNvVideoCodec 의존성이 준비되어 있어야 한다.
- 접근 가능한 H.264 또는 H.265/HEVC RTSP 영상 소스가 있어야 한다.
- 입력 주소와 전송 방식을 포함한 파이프라인 설정 파일이 있어야 한다.

## 정적 검증

프로젝트 루트에서 다음 명령을 실행한다.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m py_compile src\nvidia_pipe\receive.py
```

명령이 오류 없이 끝나야 한다.

## 단위 검증

프로젝트 루트에서 다음 명령을 실행한다.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py" -v
```

수신 패킷의 bitstream 버퍼 소유권, 연결 실패 뒤 재시도, 미지원 코덱 거부를 검증하는
모든 테스트가 통과해야 한다.

## 정상 수신 검증

1. 설정 파일의 입력 RTSP 주소를 접근 가능한 지원 코덱 영상 소스로 설정한다.
2. 파이프라인을 실행한다.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m nvidia_pipe.cli -c pipe.yml
```

3. 로그에서 수신 연결 시도와 스트림 해상도, 프레임 속도, 코덱, 시간 기준을 확인한다.
4. 후속 디코드·송출 단계가 프레임을 처리하는지 확인한다.

## 재연결 검증

1. 정상 수신이 확인된 뒤 RTSP 소스를 일시적으로 중단한다.
2. 연결 실패 로그와 3초 대기 후 재연결 시도 로그를 확인한다.
3. 소스를 다시 시작하고 새 패킷 전달이 재개되는지 확인한다.

## 미지원 코덱 검증

1. 지원 대상이 아닌 코덱의 RTSP 소스를 사용한다.
2. 지원하지 않는 코덱을 나타내는 오류가 기록되고 유효하지 않은 패킷이 후속 단계로
   전달되지 않는지 확인한다.

상세 데이터 계약은 [data-model.md](data-model.md), 선택 근거는
[research.md](research.md)를 참조한다.

## 현재 검증 결과

- 2026-09-14: `receive.py`와 `stream.py`의 구문 검사를 통과했다.
- 2026-09-14: 모의 RTSP·NVDEC 단위 검증 3건을 통과했다.
- 실제 RTSP 소스, NVIDIA GPU, NVDEC를 사용하는 통합 검증은 이 작업 환경에서 수행하지
  않았다. 배포 전 대상 환경에서 정상 수신·재연결·미지원 코덱 절차를 수행해야 한다.
