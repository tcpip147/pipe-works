# Feature Addendum: Out-of-Order Frames

**Feature identifier**: `005-pipeline-cli-orchestration`

- **FR-016**: The receive stage shall retain a global
  `out_of_order_frame_count` for input packets whose PTS is not later than
  the preceding known PTS.
- The counter increments at the same receive-stage decision that clamps a
  non-positive PTS duration to zero, and resets for each pipeline run.
  Packets without PTS or DTS do not increment it.
- **SC-008**: Packets with PTS 10, 8, and 12 produce one out-of-order frame.
