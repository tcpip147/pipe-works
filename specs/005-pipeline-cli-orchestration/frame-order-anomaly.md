# Feature Addendum: Out-of-Order Frames

**Feature identifier**: `005-pipeline-cli-orchestration`

- **FR-016**: The receive stage shall retain a global
  `out_of_order_frame_count` for input packets whose PTS is not later than
  the preceding known PTS.
- The counter resets for each pipeline run. Missing or incomparable PTS values
  do not increment it.
- **SC-008**: Frames with PTS 10, 8, and 12 produce one out-of-order frame.
