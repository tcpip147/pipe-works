# 빠른 검증: HTTP 파이프라인 제어

## 사전 조건

- Python 환경을 `uv sync`로 준비한다.
- `plumber.yml`이 하나 이상의 고유한 이름을 가진 파이프라인 설정을 가리킨다.
- 실제 시작 검증을 수행하려면 각 RTSP·CUDA 설정이 실행 가능한 환경이어야 한다.

## 실행

```powershell
uv run plumber --config plumber.yml --host 127.0.0.1
```

## 검증 시나리오

새 PowerShell 창에서 다음을 실행한다.

```powershell
Invoke-RestMethod http://127.0.0.1:8900/api/pipelines
Invoke-RestMethod -Method Post http://127.0.0.1:8900/api/pipelines/pipe1/start
Invoke-RestMethod http://127.0.0.1:8900/api/pipelines/pipe1
Invoke-RestMethod -Method Post http://127.0.0.1:8900/api/pipelines/pipe1/stop
```

목록에서 `pipe1`을 확인하고, 시작 뒤 `running`, 중지 뒤 `stopped` 상태가 반환되는지 확인한다. 브라우저로 `http://127.0.0.1:8900/`를 열어 동일한 동작을 확인한다.

## 자동 검증

```powershell
uv run python -m unittest tests.plumber.test_cli
```
