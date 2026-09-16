# Research

Use file revision `(mtime_ns, size)` to avoid reload work for unchanged modules. Load each candidate as a fresh module object, verify callable `on_frame`, calculate its supported signature, then atomically replace the active module record. Keep the old record on every error.
