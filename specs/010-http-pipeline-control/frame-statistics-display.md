# Feature Addendum: Frame Statistics Display

**Feature identifier**: `010-http-pipeline-control`  
**Status**: Extended specification

## User Scenario

An operator viewing the pipeline dashboard needs to compare each pipeline's
current frame totals and determine, without leaving its card, whether its
input and output RTSP connections are connected or disconnected.

## Functional Requirements

- **FR-012**: Every pipeline card displays the five latest frame statistics
  returned with its pipeline status.
- **FR-013**: Statistics use clear received, sent, inference-success,
  inference-failure, and out-of-order labels and remain readable on narrow
  screens.
- **FR-014**: A missing or not-yet-reported statistic displays as zero rather
  than breaking the dashboard.
- **FR-015**: The dashboard refresh updates the displayed statistics together
  with pipeline state every second.
- **FR-016**: Every pipeline card displays input and output RTSP connection
  statuses separately from the pipeline execution state.
- **FR-017**: The dashboard distinguishes `connected` and `disconnected` RTSP
  statuses clearly. A `running` pipeline does not imply
  that either RTSP connection is connected.
- **FR-018**: Input and output RTSP statuses are displayed side by side in the
  card's Endpoint area, not as frame-statistic cells.
- **FR-019**: A `stopped` card, or a card retained after a dashboard status
  request fails, displays both RTSP statuses as `disconnected` and does not
  retain a stale `running` or `Streaming` indication.
- **FR-020**: Refreshing an existing pipeline updates its displayed values
  without replacing its card or control elements.

## Success Criteria

- An operator can read all five latest totals for each visible pipeline from a
  single dashboard card.
- A pipeline that has not reported statistics still renders a complete card
  with five zero values and both RTSP statuses shown as `disconnected`.
- An operator can identify which side of a pipeline is disconnected from one
  dashboard card, even while the pipeline remains `running`.
- During normal periodic refreshes, an operator's interaction with an existing
  pipeline card is not interrupted by replacement of that card.
