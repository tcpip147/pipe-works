# Feature Specification: Safe Model Hot Reload

**Feature Branch**: `012-model-hot-reload`  
**Created**: 2026-09-16  
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Apply a valid model edit (Priority: P1)

An operator saves a valid replacement for the configured model Python file while a pipeline runs. Subsequent frames use the new callback without restarting the pipeline.

**Independent Test**: Modify a temporary model file between frames and verify the second frame is handled by the replacement callback.

**Acceptance Scenarios**:

1. **Given** a running model, **When** its source file changes to valid callback code, **Then** the next frame is processed by the replacement callback.
2. **Given** an unchanged model file, **When** frames are processed, **Then** no replacement load is attempted.

### User Story 2 - Survive an invalid save (Priority: P2)

An operator's editor temporarily saves invalid or incomplete model code. The running stream continues using the last successful model until a valid version is saved.

**Independent Test**: Replace a working temporary model with invalid Python and verify the previous callback still processes frames.

**Acceptance Scenarios**:

1. **Given** a model file with a syntax or import error, **When** reload is attempted, **Then** the pipeline logs the failure and retains the current model.
2. **Given** replacement code without a callable `on_frame`, **When** reload is attempted, **Then** the pipeline retains the current model.

### Edge Cases

- The file changes while it is read; an unsuccessful load preserves the active model.
- A replacement switches between the two-argument and parameter-aware callback forms.
- A callback error after a successful replacement is handled by the existing per-frame error path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect revisions of the configured model source file while processing frames.
- **FR-002**: The system MUST load and validate a replacement model before replacing the active callback.
- **FR-003**: The system MUST replace the active model only after successful loading and validation, at a frame boundary.
- **FR-004**: The system MUST retain the last successful model and continue the stream if replacement loading or validation fails.
- **FR-005**: The system MUST log successful replacements and failed replacement attempts.
- **FR-006**: The system MUST recalculate callback parameter compatibility for each successful replacement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A valid model edit is used by the next processed frame without a process restart.
- **SC-002**: 100% of failed replacement loads preserve frame processing with the prior active model in automated tests.
- **SC-003**: Both supported callback forms remain usable before and after a replacement.

## Assumptions

- Reloading intentionally creates a fresh module, so module-global model state is reset on successful replacement.
- Only the configured model source file is monitored; imported dependency files are outside this feature's scope.
