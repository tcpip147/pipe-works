# 작업 목록: GPU 추론 결과 CPU 큐

**입력**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`

## 1단계: 기반 계약

- [X] T001 `tests/nvidia_pipe/test_stream.py`에 `GpuFrame.inference_result`의 기본값·조회·교체 테스트를 작성한다.
- [X] T002 `src/nvidia_pipe/stream.py`에 선택적 `inference_result` 프로퍼티와 setter를 추가한다.

## 2단계: 사용자 스토리 1 - 최신 추론 결과 소비 (우선순위: P1)

**목표**: GPU 추론 결과가 있는 프레임에서만 완료된 CPU 텐서를 최신 우선 큐에 제공한다.

**독립 검증**: GPU 결과 제출, 결과 없음 건너뛰기, 큐 포화 시 오래된 결과 제거를 단위 테스트로 검증한다.

- [X] T003 [US1] `tests/nvidia_pipe/test_infer_queue.py`에 결과 없음·비CUDA 결과 거부·최신 우선 큐 정책 테스트를 작성한다.
- [X] T004 [US1] `src/nvidia_pipe/infer_queue.py`에 CUDA copy stream, pinned CPU 버퍼, 완료 event 확인 및 최신 우선 CPU 큐를 구현한다.
- [X] T005 [US1] `examples/inference.py`가 추론 프레임의 차량 상자 GPU 텐서를 `GpuFrame.inference_result`에 기록하도록 변경하고 기존 로컬 dispatcher를 제거한다.
- [X] T006 [US1] `tests/nvidia_pipe/test_cli.py`에 프레임별 결과 검사·제출·결과 없음 건너뛰기 테스트를 추가한다.
- [X] T007 [US1] `src/nvidia_pipe/cli.py`가 콜백 반환 프레임의 `inference_result`를 `infer_queue`에 비차단 제출하고 종료 시 dispatcher를 정리하도록 구현한다.

## 3단계: 마무리

- [X] T008 `specs/013-gpu-result-queue/quickstart.md`의 단위 검증과 전체 단위 테스트·문법 검사를 실행한다.
- [X] T009 `specs/013-gpu-result-queue/`의 명세·계획·작업과 구현의 일치 여부를 검토한다.
- [X] T010 `src/nvidia_pipe/infer_queue.py`에 CPU 결과 소비 daemon thread와 비어 있는 큐 대기·소비 callback 테스트를 추가한다.
- [X] T011 `src/nvidia_pipe/cli.py`가 선택적 `postprocess` 모듈의 `on_inference_result` callback을 로드해 `infer_queue` 소비자에 연결하도록 구현·검증한다.
- [X] T012 `src/nvidia_pipe/cli.py`가 `postprocess` 파일 변경을 결과 소비 thread에서 핫스왑하고, 무효한 변경에는 마지막 정상 콜백을 유지하도록 구현·검증한다.

## 의존성 및 실행 순서

`T001 → T002 → T003 → T004 → T005/T006 → T007 → T008 → T009`

`T005`와 `T006`은 서로 다른 파일을 수정하므로 T004 이후 병렬 진행할 수 있다.

## 구현 전략

MVP는 T001~T007이다. 이 범위만으로 콜백이 결과를 프레임에 기록하고 CLI가 영상 경로를 막지 않은 채 CPU 큐에 완료 결과를 제공한다.
