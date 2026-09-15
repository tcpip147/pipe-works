# Tasks: Frame Statistics Display and RTSP Connection Status

- [X] T011 Add five statistic cells to the pipeline-card layout.
- [X] T012 Render and format latest status statistics with zero fallbacks.
- [X] T013 Verify the served dashboard includes the statistics UI.
- [X] T014 Add input and output RTSP status fields to the displayed statistics contract.
- [X] T015 Render separate input/output connection-status indicators with distinct connected and disconnected states.
- [X] T016 Verify the dashboard reflects RTSP status transitions independently of pipeline execution state.
- [X] T017 Display Input and Output RTSP statuses side by side in the Endpoint area and reserve statistic cells for frame totals.
- [X] T018 On `stopped` state or dashboard status-request failure, normalize the card's execution, Endpoint, and RTSP displays to safe stopped/disconnected values.
- [X] T019 Update existing cards in place during periodic refreshes so controls and user interaction are not replaced.
