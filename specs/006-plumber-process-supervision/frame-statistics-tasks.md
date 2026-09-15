# Tasks: Frame Statistics Reporting and RTSP Connection Status

- [X] T005 Add plumber HTTP acceptance and status exposure tests.
- [X] T006 Add pipeline HTTP statistics-posting tests.
- [X] T007 Implement a one-second background reporter in `nvidia_pipe`.
- [X] T008 Implement plumber validation, storage, and child endpoint wiring.
- [X] T009 Add input RTSP connection and reconnection status tests.
- [X] T010 Add output RTSP status tests based on the existing successful-mux heartbeat and heartbeat timeout.
- [X] T011 Include both RTSP statuses in the pipeline statistics snapshot and reset them to `disconnected` for a new run.
- [X] T012 Validate, store, and return the two RTSP status fields with the existing frame counters.
- [X] T013 Verify invalid RTSP status values and incomplete seven-field snapshots are rejected without replacing the latest valid snapshot.
