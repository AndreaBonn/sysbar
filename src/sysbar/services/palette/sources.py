"""Turning session data into palette entries.

Pure builders rather than objects with a lifetime: each takes the data it lists
and the callable that acts on a choice, and returns rows. The feature assembles
them, so nothing here knows about GTK, and every rule below (what is masked,
what is unavailable, what a row is called) is testable on plain values.

Clipboard entries are masked when their content looks like a credential. That is
the one rule here that exists for a reason other than tidiness: the palette makes
the whole history searchable from a global shortcut, which is a wider exposure
than a window the user opens deliberately.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

from ..audio.models import AudioDevice
from ..clipboard.models import ClipEntry
from ..clipboard.sensitive_text import looks_like_secret, mask
from ..scenes.models import Scene
from ..shelf.models import ShelfItem
from .models import EntryKind, PaletteEntry, Runnable, Unavailable

# Pinned clipboard entries and the active scene sort above their peers.
_WEIGHT_PINNED = 10
_WEIGHT_ACTIVE = 10


def clipboard_entries(
    clips: Sequence[ClipEntry], on_copy: Callable[[str], None]
) -> list[PaletteEntry]:
    """One row per clipboard entry, masked when it looks like a credential."""
    return [_clip_entry(clip, on_copy) for clip in clips]


def _clip_entry(clip: ClipEntry, on_copy: Callable[[str], None]) -> PaletteEntry:
    secret = looks_like_secret(clip.text)
    return PaletteEntry(
        id=f"clip:{clip.id}",
        title=mask(clip.text) if secret else clip.label,
        subtitle="Copy to clipboard",
        kind=EntryKind.CLIPBOARD,
        activation=Runnable(invoke=lambda: on_copy(clip.text)),
        # Matched against the real text either way, so a masked entry stays
        # findable by typing what it contains.
        search_text=clip.text,
        masked=secret,
        weight=_WEIGHT_PINNED if clip.pinned else 0,
    )


def shelf_entries(items: Sequence[ShelfItem], on_open: Callable[[str], None]) -> list[PaletteEntry]:
    """One row per shelf item; items with nothing to open say so."""
    return [_shelf_entry(item, on_open) for item in items]


def _shelf_entry(item: ShelfItem, on_open: Callable[[str], None]) -> PaletteEntry:
    uri = item.open_uri
    activation = (
        Runnable(invoke=lambda: on_open(uri))
        if uri is not None
        else Unavailable(reason="This item has nothing to open")
    )
    return PaletteEntry(
        id=f"shelf:{item.id}",
        title=item.label,
        subtitle="Open from the shelf",
        kind=EntryKind.SHELF,
        activation=activation,
    )


def scene_entries(
    scenes: Iterable[Scene],
    active_id: str,
    on_activate: Callable[[str], None],
    display_name: Callable[[Scene], str],
) -> list[PaletteEntry]:
    """One row per scene, with the active one weighted to the top."""
    return [
        PaletteEntry(
            id=f"scene:{scene.id}",
            title=display_name(scene),
            subtitle="Active scene" if scene.id == active_id else "Activate scene",
            kind=EntryKind.SCENE,
            activation=Runnable(invoke=_activator(scene.id, on_activate)),
            weight=_WEIGHT_ACTIVE if scene.id == active_id else 0,
        )
        for scene in scenes
    ]


def _activator(value: str, action: Callable[[str], None]) -> Callable[[], None]:
    """Bind ``value`` now, so a loop does not hand every row the last one."""
    return lambda: action(value)


def device_entries(
    devices: Sequence[AudioDevice], on_select: Callable[[str], None], subtitle: str
) -> list[PaletteEntry]:
    """One row per selectable audio device; the current default is not actionable."""
    return [_device_entry(device, on_select, subtitle) for device in devices]


def _device_entry(
    device: AudioDevice, on_select: Callable[[str], None], subtitle: str
) -> PaletteEntry:
    activation = (
        Unavailable(reason="Already the default device")
        if device.is_default
        else Runnable(invoke=lambda: on_select(device.name))
    )
    return PaletteEntry(
        id=f"device:{device.kind}:{device.name}",
        title=device.description or device.name,
        subtitle=subtitle,
        kind=EntryKind.DEVICE,
        activation=activation,
    )
