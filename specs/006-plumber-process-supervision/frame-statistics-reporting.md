# Feature Addendum: Frame Statistics Reporting

**Feature identifier**: `006-plumber-process-supervision`  
**Status**: Implemented

## User Scenario

An operator needs each running pipeline's latest frame processing totals through
the plumber control service, without attaching to the pipeline process.

## Functional Requirements

- **FR-009**: A running pipeline reports its received-frame, sent-frame,
  successful-inference, failed-inference, and input timestamp-order-anomaly
  totals to plumber every second.
- **FR-010**: Plumber accepts an update only for a configured pipeline and
  retains the latest valid set of five non-negative integer totals. The update
  must contain exactly the defined statistic fields.
- **FR-011**: Starting a pipeline resets plumber's retained totals for that
  pipeline. A statistics delivery failure does not stop video processing.
- **FR-012**: The latest retained totals are returned with the existing
  pipeline status representation.

## Success Criteria

- Within one second of a running pipeline's counter update, an operator can
  obtain the five latest totals through plumber's open HTTP control service.
- Invalid or unknown-pipeline statistics updates are rejected without changing
  stored totals.

## Assumptions

- Child pipeline processes and plumber run on the same host; plumber provides a
  loopback endpoint to each child when it starts it.
- The reporting interval is fixed at one second for this feature.
- A final snapshot is sent while the pipeline entry point shuts down, before
  its sender is stopped.
