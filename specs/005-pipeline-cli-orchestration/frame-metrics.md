# Feature Addendum: Frame Metrics

**Feature identifier**: `005-pipeline-cli-orchestration`  
**Status**: Implemented

## User Scenario

An operator or an in-process monitor needs to inspect the current pipeline's
frame throughput and inference outcome totals. Starting a new pipeline must
not retain totals from the prior pipeline.

## Functional Requirements

- **FR-011**: The pipeline retains global counters for decoded frames, frames
  submitted for sending, successful inference frames, failed inference frames,
  and input timestamp-order anomalies.
- **FR-012**: All counters reset to zero before each pipeline run begins.
- **FR-013**: Receiving a decoded frame increments the received-frame counter.
- **FR-014**: Submitting a packet to the sender increments the sent-frame
  counter after that submission succeeds.
- **FR-015**: Only an inference attempt requested with `infer=True` affects
  the inference counters. A successful call increments success; an exception
  increments failure. Frames skipped by the inference interval affect neither.

## Success Criteria

- With two received frames, one successful inference, one failed inference, and
  two accepted outgoing packets, the counters report 2, 2, 1, and 1.
- Beginning a new pipeline run makes all five counters report zero before the
  first frame is processed.

## Global Counter Contract

| Metric | Global variable |
| --- | --- |
| Received frames | `received_frame_count` |
| Submitted packets | `sent_frame_count` |
| Successful inference frames | `inference_success_frame_count` |
| Failed inference frames | `inference_failure_frame_count` |
| Input PTS order anomalies | `out_of_order_frame_count` |
