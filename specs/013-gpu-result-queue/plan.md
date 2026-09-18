# 구현 계획: GPU 추론 결과 CPU 큐

**브랜치**: `013-gpu-result-queue`
**작성일**: 2026-09-18
**명세**: [spec.md](spec.md)

## 요약

각 `GpuFrame`이 선택적 GPU 추론 결과를 운반하도록 확장한다. 파이프라인 CLI는 결과가 있는 프레임마다 공통 `infer_queue`에 전달을 요청한다. 큐 모듈은 별도 CUDA copy stream과 pinned CPU 버퍼를 사용해 복사를 예약하고, 완료 event를 비차단 확인하는 daemon worker가 완료된 결과만 CPU 큐에 공개한다.

## 기술 맥락

**언어/버전**: Python 3.11.9
**주요 의존성**: PyTorch CUDA 12.1, PyNvVideoCodec
**저장소**: 프로세스 메모리의 bounded CPU 큐
**테스트**: `unittest`
**대상 플랫폼**: NVIDIA CUDA를 사용하는 Windows 파이프라인 프로세스
**프로젝트 유형**: 실시간 영상 CLI 파이프라인
**성능 목표**: 결과 전달이 NVDEC → 추론 → NVENC 프레임 제출을 대기시키지 않는다.
**제약**: 프레임 전체는 CPU로 복사하지 않으며, CPU 큐에는 복사 완료된 추론 결과만 들어간다. 큐 포화 시 최신 결과를 보존한다.
**범위**: `GpuFrame`, `infer_queue`, 파이프라인 CLI, YOLO 예제 및 관련 단위 테스트

## 헌법 준수 확인

- 실시간성: 최신 결과 우선 정책으로 큐 포화가 프레임 처리 지연으로 바뀌지 않는다.
- GPU 경로: 영상 프레임은 GPU에 유지하고 모델 결과만 pinned CPU 버퍼로 복사한다.
- 관측 가능성: 결과 전달 오류는 프레임 처리 오류와 구분해 로그로 남긴다.
- 수명주기: `nvidia_pipe`가 결과 dispatcher를 시작·종료하며 daemon worker가 파이프라인 종료를 막지 않는다.

## 설계 결정

1. `GpuFrame.inference_result`는 기본값 `None`인 선택 속성이다. 콜백은 실제 추론을 수행한 프레임에만 GPU 텐서를 설정한다.
2. CLI는 콜백 반환 직후 `inference_result`를 검사하고, 결과가 있으면 `infer_queue`에 제출한다. 인코더에는 동일 프레임을 그대로 전달한다.
3. `infer_queue`는 producer stream의 완료 event에 의존하는 전용 copy stream에서 GPU→pinned CPU 비동기 복사를 예약한다.
4. daemon worker는 `Event.query()`만 사용해 완료 여부를 확인한다. 메인 스레드와 worker 모두 `synchronize()`를 호출하지 않는다.
5. 완료된 CPU 텐서는 bounded `Queue`에 넣는다. 큐가 가득 차면 가장 오래된 항목을 제거하고 새 항목을 넣는다.
6. CLI 종료 시 dispatcher의 worker와 대기 항목을 정리한다.
7. CPU 큐 소비는 별도 daemon thread가 담당한다. 큐가 비었을 때 해당 thread만 조건 대기하며, 기본 소비자는 결과 형태를 debug 로그로 남긴다. 전송 소비자는 같은 callback 지점에 연결한다.
8. YAML의 선택적 `postprocess` 경로는 동적 모듈로 로드한다. 모듈은 CPU 결과 소비 thread에서 호출할 `on_inference_result` 함수를 제공해야 하며, 파일 변경은 다음 결과 소비 전에 감지해 유효한 새 콜백으로 교체한다. 변경 중 문법 오류 등으로 재로딩에 실패하면 마지막 정상 콜백을 유지한다.

## 프로젝트 구조

```text
specs/013-gpu-result-queue/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md

src/nvidia_pipe/
├── stream.py          # GpuFrame 결과 속성
├── infer_queue.py     # 비동기 복사 및 CPU 결과 큐
└── cli.py             # 프레임마다 결과 제출과 종료

examples/inference.py  # 차량 검출 결과를 프레임에 기록
tests/nvidia_pipe/
├── test_stream.py
├── test_infer_queue.py
└── test_cli.py
```

## 복잡성 추적

추가 복잡성은 GPU 완료 event 확인과 bounded 큐뿐이다. 이는 프레임 처리 경로의 동기 복사를 피하기 위해 필요하며, 별도 프로세스나 CUDA IPC는 사용하지 않는다.

<!-- Legacy template retained below for tool bootstrap history; it is not part of this plan.

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `$speckit-plan` command; its definition describes the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
-->
