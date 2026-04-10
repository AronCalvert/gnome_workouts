from __future__ import annotations

import sys

_ready = False
_available = False
_pipelines: dict[str, object] = {}

_PIPELINE_DESCS: dict[str, str] = {
    "bell": (
        "audiotestsrc wave=sine freq=880 samplesperbuffer=4410 num-buffers=2 "
        "! audioconvert ! autoaudiosink"
    ),
    "complete": (
        "audiotestsrc wave=sine freq=528 samplesperbuffer=4410 num-buffers=6 "
        "! audioconvert ! autoaudiosink"
    ),
}


def _init() -> bool:
    global _ready, _available
    if _ready:
        return _available
    _ready = True
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        Gst.init(None)
        _available = True
        return True
    except Exception as e:
        print(f"sound: GStreamer init failed: {e}", file=sys.stderr)
        return False


def play(event_id: str) -> None:
    if not _init():
        return
    desc = _PIPELINE_DESCS.get(event_id)
    if not desc:
        return
    from gi.repository import Gst

    try:
        pipeline = _pipelines.get(event_id)
        if pipeline is None:
            pipeline = Gst.parse_launch(desc)
            _pipelines[event_id] = pipeline
        pipeline.set_state(Gst.State.NULL)
        pipeline.set_state(Gst.State.PLAYING)
    except Exception as e:
        print(f"sound: play({event_id!r}) failed: {e}", file=sys.stderr)
