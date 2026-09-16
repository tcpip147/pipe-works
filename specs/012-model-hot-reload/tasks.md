# Tasks: Safe Model Hot Reload

## Phase 1: Setup

- [X] T001 Review model reload contract in specs/012-model-hot-reload/contracts/model-reload.md

## Phase 2: Foundational

- [X] T002 Add a revision-aware active model holder in src/nvidia_pipe/cli.py

## Phase 3: User Story 1 - Apply a valid model edit (Priority: P1)

- [X] T003 [US1] Add valid source-change replacement tests in tests/nvidia_pipe/test_cli.py
- [X] T004 [US1] Safely swap loaded model callbacks at frame boundaries in src/nvidia_pipe/cli.py

## Phase 4: User Story 2 - Survive an invalid save (Priority: P2)

- [X] T005 [US2] Add failed reload retention tests in tests/nvidia_pipe/test_cli.py
- [X] T006 [US2] Log candidate load or callback validation failures while retaining the active model in src/nvidia_pipe/cli.py

## Phase 5: Polish

- [X] T007 Update model author documentation in README.md
- [X] T008 Run the complete unit suite and mark tasks complete in specs/012-model-hot-reload/tasks.md
