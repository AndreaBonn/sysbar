"""Audio mixer models and the pure sink-input grouping logic.

A *sink-input* is one audio stream. The mixer groups streams by application so
the user controls one volume per app. Grouping is a pure function, tested with
concrete inputs; ``pulsectl`` lives behind the backend adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SinkInput:
    """One PulseAudio/PipeWire audio stream."""

    index: int
    app_id: str | None = None
    binary: str | None = None
    name: str | None = None
    pid: int | None = None
    volume: float = 1.0
    muted: bool = False
    corked: bool = True


@dataclass(frozen=True)
class MixerApp:
    """All audio streams of one application, controlled together."""

    id: str
    name: str
    volume: float
    is_playing: bool
    muted: bool
    sink_input_indices: list[int] = field(default_factory=list)


def stable_app_id(sink_input: SinkInput) -> str:
    """Return a stable identity for a stream.

    Prefers the application id, then the process binary (PIDs are recycled but
    binaries are not), then the stream name, finally the index.
    """
    return (
        sink_input.app_id
        or sink_input.binary
        or sink_input.name
        or f"sink-input-{sink_input.index}"
    )


def group_sink_inputs(sink_inputs: list[SinkInput]) -> list[MixerApp]:
    """Group streams into per-application mixer entries, order-preserving.

    The group volume is taken from the first stream; the group plays if any
    stream is uncorked; the group is muted only if every stream is muted.
    """
    order: list[str] = []
    grouped: dict[str, list[SinkInput]] = {}
    for sink_input in sink_inputs:
        key = stable_app_id(sink_input)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(sink_input)

    apps: list[MixerApp] = []
    for key in order:
        streams = grouped[key]
        first = streams[0]
        apps.append(
            MixerApp(
                id=key,
                name=first.name or first.binary or key,
                volume=first.volume,
                is_playing=any(not stream.corked for stream in streams),
                muted=all(stream.muted for stream in streams),
                sink_input_indices=[stream.index for stream in streams],
            )
        )
    return apps
