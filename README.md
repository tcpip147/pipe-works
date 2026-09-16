# pipe-works

## Frame Statistics Dashboard

When a pipeline is started by `plumber`, its `nvidia-pipe` child reports a
statistics snapshot to the local plumber HTTP service every second. The
dashboard refreshes the same values automatically and displays them on each
pipeline card.

Each pipeline status response contains a `statistics` object with:

| Field | Meaning |
| --- | --- |
| `received_frame_count` | Number of decoded frames received by the pipeline |
| `sent_frame_count` | Number of encoded packets accepted by the sender |
| `inference_success_frame_count` | Frames whose requested inference completed successfully |
| `inference_failure_frame_count` | Frames whose requested inference raised an error |
| `out_of_order_frame_count` | Input packets with PTS that is not later than the previous known PTS |
| `input_rtsp_status` | Input RTSP connection: `disconnected` or `connected` |
| `output_rtsp_status` | Output RTSP connection: `disconnected` or `connected` |

The `POST /api/pipelines/{name}/statistics` endpoint is used internally by
the locally spawned pipeline process. It accepts the five counter fields as
non-negative integers and both RTSP status fields as defined status strings.
Invalid reports and unknown pipeline names are rejected.
If a report cannot be delivered, video processing continues; plumber retains
the last successfully received snapshot. A newly started pipeline begins with
all statistics set to zero.

The dashboard shows Input and Output RTSP statuses side by side in each
pipeline card's Endpoint area. A stopped card, or a card retained after the
dashboard cannot retrieve pipeline status, displays both RTSP statuses as
`disconnected` and shows the endpoint as stopped. Periodic updates preserve
existing cards and controls rather than replacing the whole dashboard.

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
# HTTP 제어 서버 실행
uv run plumber --config plumber.yml --host 127.0.0.1

# Windows 배치 파일로 실행
.\run.bat

# 단일 파이프라인을 직접 실행
uv run nvidia-pipe --config pipe.yml
```

브라우저에서 `http://127.0.0.1:8900`을 열어 파이프라인을 시작하거나 중지할 수 있습니다. 실행 중에는 `Ctrl+C`로 서버와 실행 중인 파이프라인을 종료할 수 있습니다.

### REST API

| 요청 | 설명 |
| --- | --- |
| `GET /api/pipelines` | 등록된 모든 파이프라인의 상태 조회 |
| `GET /api/pipelines/{name}` | 특정 파이프라인의 상태 조회 |
| `POST /api/pipelines/{name}/start` | 특정 파이프라인 시작 |
| `POST /api/pipelines/start-all` | 등록된 모든 파이프라인 시작 |
| `POST /api/pipelines/{name}/stop` | 특정 파이프라인 중지 |

예시:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8900/api/pipelines/pipe1/start
Invoke-RestMethod http://127.0.0.1:8900/api/pipelines
```

## 설정

### 파이프라인 목록: `plumber.yml`

```yaml
pipelines:
  - config: pipe.yml
  - config: pipe2.yml
```

`auto_start: true`를 `plumber.yml` 최상위에 추가하면 `plumber` 앱이 시작될 때 등록된
모든 파이프라인을 자동으로 시작합니다. 생략하거나 `false`로 설정하면 기존처럼 화면 또는
API를 통해 수동으로 시작합니다.

`port`는 plumber HTTP 서버가 사용할 포트입니다.

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
  parameters:
    font-size: 14
    yuv: [150, 43, 21]
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
| `parameters` | 모델 콜백에 전달할 임의의 YAML 매핑. 실행 중 저장하면 다음 프레임부터 반영됩니다. |

입력 코덱은 H.264와 HEVC/H.265를 지원합니다. 출력은 입력 프레임의 코덱, 해상도, 시간 기준을 유지해 송출합니다.

## 프레임 처리 모듈 작성

`inference.model`이 가리키는 파일은 아래 형식의 함수를 제공해야 합니다.

```python
from nvidia_pipe.stream import GpuFrame


def on_frame(frame: GpuFrame, infer: bool, parameters: dict) -> GpuFrame:
    # infer=True: 이번 프레임에서 추론을 수행할 차례
    # infer=False: 이전 추론 결과를 재사용할 차례
    # GPU 프레임을 수정하거나 분석한 뒤 반환
    return frame
```

기존 `on_frame(frame, infer)` 형식도 계속 지원됩니다. 실행 중에는
`inference.parameters`만 다시 읽습니다. RTSP 주소, GPU, 모델 경로 등 다른 설정을
바꾼 경우에는 파이프라인을 재시작해야 합니다. YAML이 저장 중이어서 읽을 수 없으면
마지막으로 성공한 파라미터를 계속 사용합니다.

`inference.model` 파일도 실행 중 감지합니다. 유효한 Python 파일을 저장하면 다음
프레임 경계에서 새 `on_frame` 함수로 교체됩니다. 저장 도중의 문법 오류, import 오류,
또는 `on_frame` 누락은 로그로 남기고 기존 모델을 계속 사용하므로 스트림은 중단되지
않습니다. 성공적으로 교체된 모델의 모듈 전역 상태는 새로 시작됩니다.

`inference.model` 파일도 실행 중 감지합니다. 유효한 Python 파일을 저장하면 다음
프레임 경계에서 새 `on_frame` 함수로 교체됩니다. 저장 도중의 문법 오류, import 오류,
또는 `on_frame` 누락은 로그로 남기고 기존 모델을 계속 사용하므로 스트림은 중단되지
않습니다. 성공적으로 교체된 모델의 모듈 전역 상태는 새로 시작됩니다.

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

- `plumber`: 등록된 파이프라인을 HTTP API와 브라우저 화면에서 개별 제어하는 서버를 실행합니다. 기본 주소는 `127.0.0.1:8900`입니다.
- `nvidia-pipe`: 지정한 단일 파이프라인 설정을 실행합니다.
