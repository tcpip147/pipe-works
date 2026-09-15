# Feature Addendum: Frame Statistics Reporting

**Feature identifier**: `006-plumber-process-supervision`  
**Status**: Implemented

## User Scenario

An operator needs each running pipeline's latest frame processing totals through
the plumber control service, without attaching to the pipeline process.

## Functional Requirements

- **FR-009**: A running pipeline reports its received-frame, sent-frame,
  successful-inference, failed-inference, and input timestamp-order-anomaly
  totals, plus the current input- and output-RTSP connection statuses, to
  plumber every second.
- **FR-010**: Plumber accepts an update only for a configured pipeline and
  retains the latest valid snapshot. The update must contain exactly five
  non-negative integer totals and the two defined RTSP status values.
- **FR-011**: Starting a pipeline resets plumber's retained totals for that
  pipeline. A statistics delivery failure does not stop video processing.
- **FR-012**: The latest retained totals are returned with the existing
  pipeline status representation.

## Success Criteria

- Within one second of a running pipeline's update, an operator can obtain the
  five latest totals and both RTSP connection statuses through plumber's open
  HTTP control service.
- Invalid or unknown-pipeline statistics updates are rejected without changing
  stored totals.

## Assumptions

- Child pipeline processes and plumber run on the same host; plumber provides a
  loopback endpoint to each child when it starts it.
- The reporting interval is fixed at one second for this feature.
- A final snapshot is sent while the pipeline entry point shuts down, before
  its sender is stopped.
- `input_rtsp_status` is `connected` after the input stream is opened and is
  `disconnected` before the first successful input connection and while the
  pipeline retries after an input connection or read failure.
- `output_rtsp_status` is `connected` only while the sender's latest successful
  mux heartbeat is within its heartbeat timeout. It is `disconnected` while
  the sender is retrying or being restarted, and before the first successful
  output transmission.
- Starting a pipeline initializes both RTSP status values to `disconnected`.
