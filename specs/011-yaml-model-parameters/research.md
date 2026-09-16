# Research: Live Model Parameters

## Decision: Refresh by file revision before callback invocation

Compare the configuration file's nanosecond modification time and size on each frame. Parse only when this revision changes; a successful reload replaces only `inference.parameters`. This applies edits to the next frame while avoiding hot-path YAML parsing.

## Decision: Keep legacy callback compatibility through signature inspection

Inspect the callback once after loading it to determine whether `parameters` can be supplied. This avoids catching a `TypeError` thrown by model code and preserves `on_frame(frame, infer)`.

## Decision: Validate example appearance locally with defaults

The example uses a bounded positive scale derived from `font-size` and accepts exactly three 0–255 YUV integers. Invalid or absent values fall back to `14` and `[150, 43, 21]` so a bad edit does not discard a frame.
