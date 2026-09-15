# pipe-works

NVIDIA GPU에서 RTSP 영상을 **수신 → NVDEC 디코딩 → 프레임 처리/추론 → NVENC 인코딩 → RTSP 송출**하는 Python 파이프라인입니다. 여러 파이프라인을 하나의 `plumber` 프로세스로 함께 실행할 수 있습니다.

## 주요 기능

- RTSP 입력 스트림 수신 및 연결이 끊겼을 때 재연결
- NVIDIA NVDEC/NVENC 기반 GPU 디코딩·인코딩
- PyTorch CUDA 스트림에서 GPU 프레임을 직접 처리하는 확장 지점
- 출력 RTSP 송출 프로세스 감시 및 자동 재시작
- YAML로 여러 카메라 파이프라인을 일괄 관리
- 파이프라인별 이름을 포함한 로그 출력

## 요구 사항

- Windows
- Python 3.11.9
- NVIDIA GPU 및 호환 NVIDIA 드라이버
- CUDA 12.x 런타임 (`CUDA_PATH` 또는 `CUDA_PATH_V12_6` 환경 변수)
- 입력/출력에 접근 가능한 RTSP 서버
- [uv](https://docs.astral.sh/uv/) (권장)

프로젝트는 CUDA 12.1용 PyTorch와 `PyNvVideoCodec`을 사용합니다. NVIDIA Video Codec SDK/CUDA 환경은 GPU와 드라이버 구성에 맞게 준비해야 합니다.

## 설치

```powershell
git clone <repository-url>
cd pipe-works
uv sync
```

`uv sync`가 완료되면 필요한 Python 환경은 `.venv`에 생성됩니다.

## 빠른 시작

1. `pipe.yml`의 `input.rtsp.url`과 `output.rtsp.url`을 환경에 맞게 바꿉니다.
2. `plumber.yml`에 실행할 파이프라인 설정 파일을 등록합니다.
3. 다음 중 하나를 실행합니다.

```powershell
# 모든 파이프라인 실행
uv run plumber --config plumber.yml

# Windows 배치 파일로 실행
.\run.bat

# 단일 파이프라인 실행
uv run nvidia-pipe --config pipe.yml
```

실행 중에는 `Ctrl+C`로 종료할 수 있습니다.

## 설정

### 파이프라인 목록: `plumber.yml`

```yaml
pipelines:
  - config: pipe.yml
  - config: pipe2.yml
```

각 항목은 개별 파이프라인 YAML 파일을 가리킵니다. 각 파이프라인의 `name`은 반드시 비어 있지 않고 서로 달라야 합니다.

### 개별 파이프라인: `pipe.yml`

```yaml
name: camera-1

input:
  rtsp:
    url: rtsp://input-server/live/camera-1
    transport: tcp

output:
  rtsp:
    url: rtsp://output-server:8554/camera-1
    transport: tcp

inference:
  gpuid: 0
  interval_frames: 1
  input_format: native
  frame_type: pytorch
  model: examples/inference.py
```

| 항목 | 설명 |
| --- | --- |
| `name` | 로그와 프로세스를 구분하는 고유 이름 |
| `input.rtsp` | 입력 RTSP URL 및 전송 방식 (`tcp`) |
| `output.rtsp` | 송출할 RTSP URL 및 전송 방식 (`tcp`) |
| `gpuid` | 사용할 NVIDIA GPU 번호 |
| `interval_frames` | 추론 실행 간격입니다. `1`은 매 프레임, `0`은 추론 콜백을 건너뜁니다. |
| `input_format` | 디코더 출력 형식: `native`, `rgb`, `rgbp` |
| `frame_type` | 현재 지원값은 `pytorch` |
| `model` | `on_frame` 함수를 제공하는 Python 파일 경로 |

입력 코덱은 H.264와 HEVC/H.265를 지원합니다. 출력은 입력 프레임의 코덱, 해상도, 시간 기준을 유지해 송출합니다.

## 프레임 처리 모듈 작성

`inference.model`이 가리키는 파일은 아래 형식의 함수를 제공해야 합니다.

```python
from nvidia_pipe.stream import GpuFrame


def on_frame(frame: GpuFrame, infer: bool) -> GpuFrame:
    # infer=True: 이번 프레임에서 추론을 수행할 차례
    # infer=False: 이전 추론 결과를 재사용할 차례
    # GPU 프레임을 수정하거나 분석한 뒤 반환
    return frame
```

`examples/inference.py`는 NV12 GPU 프레임의 오른쪽 위에 현재 시간을 그리는 최소 예제입니다. `torch.from_dlpack()`을 이용해 CPU 복사 없이 프레임 데이터에 접근합니다.

## 테스트

```powershell
uv run python -m unittest discover -s tests -t .
```

테스트는 설정 검증, 프로세스 정리, 코덱/송출 동작 단위, 기본 프레임 처리 예제를 다룹니다. 실제 RTSP 서버와 GPU가 필요한 통합 실행은 별도로 구성해야 합니다.

## 프로젝트 구조

```text
src/
├── nvidia_pipe/  # RTSP 수신·디코딩·인코딩·송출 및 단일 파이프라인 CLI
└── plumber/      # 여러 파이프라인을 관리하는 CLI
examples/         # 프레임 처리 모듈 예제
tests/            # 단위 테스트
pipe.yml          # 단일 파이프라인 설정 예시
plumber.yml       # 파이프라인 목록 설정 예시
```

## CLI

```text
plumber [-c CONFIG]
nvidia-pipe [-c CONFIG]
```

- `plumber`: 기본값 `plumber.yml`을 읽어 등록된 모든 파이프라인을 별도 프로세스로 실행합니다.
- `nvidia-pipe`: 지정한 단일 파이프라인 설정을 실행합니다.
