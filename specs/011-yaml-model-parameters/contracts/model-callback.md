# Model Callback Contract

Parameter-aware models may implement `on_frame(frame, infer, parameters)`. `parameters` is the current `inference.parameters` mapping. The established `on_frame(frame, infer)` form remains supported. Only `inference.parameters` reloads live; all other pipeline settings require restart.
