# Model Reload Contract

The configured `inference.model` file may change at runtime. A valid replacement must expose callable `on_frame`; it may use either `on_frame(frame, infer)` or `on_frame(frame, infer, parameters)`. Failed replacements leave the preceding callback active.
