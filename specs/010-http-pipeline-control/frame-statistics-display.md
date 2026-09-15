# Feature Addendum: Frame Statistics Display

**Feature identifier**: `010-http-pipeline-control`  
**Status**: Implemented

## User Scenario

An operator viewing the pipeline dashboard needs to compare each pipeline's
current received, sent, successful-inference, and failed-inference totals
without leaving its card.

## Functional Requirements

- **FR-012**: Every pipeline card displays the five latest frame statistics
  returned with its pipeline status.
- **FR-013**: Statistics use clear received, sent, inference-success,
  inference-failure, and out-of-order labels and remain readable on narrow
  screens.
- **FR-014**: A missing or not-yet-reported statistic displays as zero rather
  than breaking the dashboard.
- **FR-015**: The dashboard refresh updates the displayed statistics together
  with pipeline state every two seconds.

## Success Criteria

- An operator can read all five latest totals for each visible pipeline from a
  single dashboard card.
- A pipeline that has not reported statistics still renders a complete card
  with five zero values.
