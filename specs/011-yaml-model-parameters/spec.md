# Feature Specification: Live Model Parameters

**Feature Branch**: `011-yaml-model-parameters`  
**Created**: 2026-09-16  
**Status**: Draft  
**Input**: User description: "Pass YAML parameters to model callbacks, apply YAML changes without restart, and make the timestamp example use font-size and YUV."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure model rendering (Priority: P1)

An operator supplies a `parameters` mapping under `inference` in the pipeline YAML. The model callback receives that mapping for every frame and uses it to control rendering.

**Why this priority**: It makes model-specific configuration available without hard-coding it into model files.

**Independent Test**: Start a pipeline with a model that records callback arguments and verify that the YAML `parameters` mapping is received.

**Acceptance Scenarios**:

1. **Given** a valid pipeline YAML with `inference.parameters`, **When** a frame reaches a callback that accepts parameters, **Then** the callback receives the configured mapping with the frame and inference flag.
2. **Given** a model callback using the existing two-argument form, **When** it processes a frame, **Then** it continues to run without a compatibility error.
3. **Given** no `inference.parameters` section, **When** a compatible callback processes a frame, **Then** it receives an empty mapping.

---

### User Story 2 - Change parameters live (Priority: P2)

An operator edits only the YAML `inference.parameters` values while the pipeline is running. Later frames use the valid revised values without restarting the process.

**Why this priority**: Operators can tune overlays and model behavior during a live stream.

**Independent Test**: Change the configuration file between two processed frames and verify the callback receives the revised mapping on the second frame.

**Acceptance Scenarios**:

1. **Given** a running pipeline and a changed valid YAML file, **When** the next frame is processed, **Then** the callback receives the revised `parameters` mapping.
2. **Given** a changed YAML file whose non-parameter settings differ, **When** the next frame is processed, **Then** only the current `inference.parameters` mapping is adopted and pipeline setup remains unchanged.
3. **Given** an invalid or unreadable replacement YAML file, **When** a frame is processed, **Then** processing continues with the most recently valid parameters and the issue is logged.

---

### User Story 3 - Tune timestamp appearance (Priority: P3)

An operator adjusts `font-size` and a YUV triplet in the sample configuration to control the timestamp overlay's scale and color.

**Why this priority**: The example visibly demonstrates both parameter delivery and live tuning.

**Independent Test**: Invoke the sample model with two parameter sets and verify the overlay changes its pixel extent and YUV values accordingly.

**Acceptance Scenarios**:

1. **Given** valid `font-size` and `yuv` parameters, **When** the example draws the timestamp, **Then** it uses them for glyph scale and NV12 luma/chroma values.
2. **Given** omitted or malformed appearance parameters, **When** the example processes a frame, **Then** it uses documented safe defaults rather than failing the frame.

### Edge Cases

- The configuration is being written while it is read; the last valid parameter mapping remains active.
- The YAML has no `inference` mapping or its `parameters` value is not a mapping; the active mapping becomes empty only after a valid configuration is read.
- A callback rejects the optional parameter argument; its existing two-argument invocation remains supported.
- `font-size` is too small, too large, or non-numeric, and YUV is not three byte-range numeric values.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST obtain `inference.parameters` as a mapping from the pipeline YAML and make its current value available during frame processing.
- **FR-002**: The system MUST invoke parameter-aware model callbacks with the frame, inference flag, and current parameter mapping.
- **FR-003**: The system MUST preserve support for existing model callbacks that accept only the frame and inference flag.
- **FR-004**: The system MUST detect a configuration file change during processing and use parameters from the latest successfully read YAML on subsequent frames without restarting the pipeline.
- **FR-005**: The system MUST retain the last successfully read parameters if a changed configuration cannot be read or parsed, and MUST log the failure.
- **FR-006**: Live configuration refresh MUST affect only the parameter mapping; pipeline connection, GPU, model, and other startup settings remain unchanged until restart.
- **FR-007**: The timestamp sample MUST derive glyph scale from `font-size` and derive its NV12 luma and chroma overlay color from `yuv`.
- **FR-008**: The timestamp sample MUST use safe documented defaults when its appearance parameters are absent or invalid.

### Key Entities

- **Active parameters**: The last successfully loaded model-specific mapping used for callback invocation.
- **Configuration revision**: The observable state of the YAML file used to decide whether to reload its parameters.
- **Overlay appearance**: The validated font scale and YUV color derived by the sample model.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A model receives all configured parameter values on 100% of processed frames after a valid configuration load.
- **SC-002**: A valid parameter-only YAML edit is reflected on the next processed frame, with no pipeline restart.
- **SC-003**: Existing two-argument callback models process frames successfully without modification.
- **SC-004**: The sample overlay produces the configured YUV values and a scale corresponding to each valid font-size value in automated tests.

## Assumptions

- `inference.parameters` is model-owned data and must be a YAML mapping; nested values are passed through unchanged.
- File modification metadata is sufficient to avoid parsing the YAML on every frame when it has not changed.
- The optional callback argument is named `parameters`; callbacks that cannot accept it retain the legacy invocation.
- The sample uses `font-size: 14` and `yuv: [150, 43, 21]` as defaults.
