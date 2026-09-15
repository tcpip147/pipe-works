# 작업 목록: HTTP 파이프라인 제어

**입력**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/http-api.md`

## Phase 1: 기반

- [X] T001 파이프라인 정의·상태 모델과 YAML 검증을 `src/plumber/cli.py`에 구현한다.
- [X] T002 프로세스 시작·중지·강제 종료 및 서비스 종료 정리를 `src/plumber/cli.py`에 구현한다.

## Phase 2: 사용자 스토리 1 — 시작과 중지 (P1)

**독립 검증**: 시작 뒤 `running`, 중지 뒤 `stopped` 상태를 반환한다.

- [X] T003 [US1] 시작·중지 REST 요청을 `src/plumber/cli.py`에 구현한다.
- [X] T004 [US1] 중복 시작과 알 수 없는 이름을 검증하는 단위 테스트를 `tests/plumber/test_cli.py`에 추가한다.

## Phase 3: 사용자 스토리 2 — 상태 조회 (P2)

**독립 검증**: 목록 및 개별 상태에서 `stopped`, `running`, `failed`를 확인한다.

- [X] T005 [US2] 목록·개별 상태 REST 요청과 상태 표현을 `src/plumber/cli.py`에 구현한다.
- [X] T006 [US2] 상태 조회와 비정상 종료 상태를 검증하는 단위 테스트를 `tests/plumber/test_cli.py`에 추가한다.

## Phase 4: 사용자 스토리 3 — 브라우저 제어 (P3)

**독립 검증**: 기본 화면에서 목록과 시작·중지 동작을 제공한다.

- [X] T007 [US3] 로컬 브라우저 제어 화면을 `src/plumber/cli.py`에 구현한다.
- [X] T008 [US3] 실행 주소와 API 사용법을 `README.md`에 문서화한다.

## Phase 5: 검증 및 마무리

- [X] T009 `tests/plumber/test_cli.py`와 `specs/010-http-pipeline-control/quickstart.md`의 검증 명령을 실행한다.
- [X] T010 명세·계획·계약과 구현의 일치 여부를 `specs/010-http-pipeline-control/`에서 검토한다.

## 의존성

`T001 → T002 → T003 → T005 → T007 → T009 → T010` 순서다. `T004`, `T006`, `T008`은 각각 해당 기능 구현 뒤 병렬로 진행할 수 있다.
