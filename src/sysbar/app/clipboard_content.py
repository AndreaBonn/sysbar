from ..core.i18n import _

_PINNED_ICON = "starred-symbolic"
_UNPINNED_ICON = "non-starred-symbolic"


def empty_state(query: str) -> tuple[str, str]:
    """C1: say how the history fills, or that the search found nothing."""
    if query:
        return _("No entries match"), _("Try fewer letters.")
    return _("Nothing copied yet"), _(
        "Copy some text or a link anywhere: it appears here, ready to copy again."
    )


def pin_presentation(pinned: bool) -> tuple[str, str]:
    """Return the pin button's icon and translated action tooltip."""
    if pinned:
        return _PINNED_ICON, _("Unpin")
    return _UNPINNED_ICON, _("Pin")
