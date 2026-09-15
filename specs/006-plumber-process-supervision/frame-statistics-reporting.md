# Feature Addendum: Frame Statistics Reporting

**Feature identifier**: `006-plumber-process-supervision`  
**Status**: Implemented

## User Scenario

An operator needs each running pipeline's latest frame processing totals through
the plumber control service, without attaching to the pipeline process.

## Functional Requirements

- **FR-009**: A running pipeline reports its received-frame, sent-frame,
  successful-inference, and failed-inference totals to plumber every three
  seconds.
- **FR-010**: Plumber accepts an update only for a configured pipeline and
  retains the latest valid set of four non-negative integer totals.
- **FR-011**: Starting a pipeline resets plumber's retained totals for that
  pipeline. A statistics delivery failure does not stop video processing.
- **FR-012**: The latest retained totals are returned with the existing
  pipeline status representation.

## Success Criteria

- Within three seconds of a running pipeline's counter update, an operator can
  obtain the four latest totals through plumber's open HTTP control service.
- Invalid or unknown-pipeline statistics updates are rejected without changing
  stored totals.

## Assumptions

- Child pipeline processes and plumber run on the same host; plumber provides a
  loopback endpoint to each child when it starts it.
- The reporting interval is fixed at three seconds for this feature.

