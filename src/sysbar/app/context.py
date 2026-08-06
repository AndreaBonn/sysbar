"""The collaborators every feature module needs, passed as one value.

Feature modules take configuration, capability detection, notifications and the
autostart manager. Passing them individually puts every constructor at or past
the project's four-parameter cap before it takes a single collaborator of its
own, so they travel together.

The module holds no GI import at runtime: the annotations are deferred, so the
container is constructible with fakes in a test that never touches GTK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.capabilities import Capabilities
    from ..core.config import Config
    from ..services.autostart import AutostartManager
    from ..services.notifier import Notifier


@dataclass(frozen=True)
class AppContext:
    """Shared collaborators handed to every feature module."""

    config: Config
    capabilities: Capabilities
    notifier: Notifier
    autostart: AutostartManager

    def has(self, capability: str) -> bool:
        """Whether ``capability`` is present in this session.

        Delegating here keeps the capability check one call rather than two at
        each of its many call sites in the feature modules.
        """
        return bool(self.capabilities.has(capability))
