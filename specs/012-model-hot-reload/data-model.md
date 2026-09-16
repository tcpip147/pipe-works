# Data Model

| Entity | Fields | Rule |
| --- | --- | --- |
| Active model | module, callback compatibility, revision | Replaced only after a valid candidate is loaded. |
| Model revision | mtime_ns, size | Determines when another candidate load is needed. |
