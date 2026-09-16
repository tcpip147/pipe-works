# Tasks: Live Model Parameters

**Input**: Design documents from `/specs/011-yaml-model-parameters/`

## Phase 1: Setup

- [X] T001 Review the callback contract and quickstart in specs/011-yaml-model-parameters/contracts/model-callback.md and specs/011-yaml-model-parameters/quickstart.md

## Phase 2: Foundational

- [X] T002 Add a revision-aware live parameter provider and callback compatibility detection in src/nvidia_pipe/cli.py

## Phase 3: User Story 1 - Configure model rendering (Priority: P1)

**Goal**: Pass the YAML mapping to parameter-aware callbacks without breaking legacy models.

**Independent Test**: A mocked pipeline invokes both callback forms successfully and captures the expected mapping.

- [X] T003 [US1] Add callback parameter and legacy compatibility tests in tests/nvidia_pipe/test_cli.py
- [X] T004 [US1] Dispatch active parameters to compatible model callbacks in src/nvidia_pipe/cli.py

## Phase 4: User Story 2 - Change parameters live (Priority: P2)

**Goal**: Apply valid YAML parameter edits to subsequent frames while retaining last valid values on failure.

**Independent Test**: A changed temporary YAML file produces a new callback mapping; malformed YAML retains the prior mapping.

- [X] T005 [US2] Add successful reload and invalid reload retention tests in tests/nvidia_pipe/test_cli.py
- [X] T006 [US2] Refresh only inference parameters from changed YAML revisions in src/nvidia_pipe/cli.py

## Phase 5: User Story 3 - Tune timestamp appearance (Priority: P3)

**Goal**: Render timestamp size and color from `font-size` and YUV parameters.

**Independent Test**: Example frames contain configured YUV values and altered glyph scales.

- [X] T007 [US3] Add parameterized overlay and fallback tests in tests/test_inference_example.py
- [X] T008 [US3] Validate overlay parameters and use them in examples/inference.py

## Phase 6: Polish & Validation

- [X] T009 Update YAML/model callback documentation in README.md
- [X] T010 Run the unit suite from quickstart.md and mark all tasks complete in specs/011-yaml-model-parameters/tasks.md

## Dependencies & Execution Order

`T001 → T002 → T003/T004 → T005/T006 → T007/T008 → T009 → T010`. Tests precede their corresponding implementation task. User stories share the CLI foundation and therefore run sequentially.

## Implementation Strategy

Deliver and validate the callback contract first (MVP), then live refresh, then the visible example behavior.
