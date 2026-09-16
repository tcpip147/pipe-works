# Data Model: Live Model Parameters

| Entity | Fields | Rules |
| --- | --- | --- |
| Active parameters | mapping, file revision | Last valid `inference.parameters`; defaults to empty mapping. |
| File revision | mtime_ns, size | Determines whether a YAML refresh is needed. |
| Overlay appearance | font size, YUV | Font size is bounded; YUV is three byte-range integers. |
