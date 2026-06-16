"""On-demand bandwidth test (port of ``SpeedTest``).

The throughput calculation is pure and unit-tested; the download against a
configurable endpoint is the boundary and runs off the GTK main loop.
"""

from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

_BITS_PER_BYTE = 8
_BITS_PER_MEGABIT = 1_000_000
_CHUNK_SIZE = 65_536
_DOWNLOAD_TIMEOUT_SECONDS = 30


def throughput_mbps(byte_count: int, seconds: float) -> float:
    """Megabits per second for ``byte_count`` transferred in ``seconds``."""
    if seconds <= 0:
        return 0.0
    return (byte_count * _BITS_PER_BYTE) / (seconds * _BITS_PER_MEGABIT)


class SpeedTestService:
    """Measure download bandwidth against a configurable endpoint."""

    def download_mbps(self, url: str) -> float | None:
        """Download ``url`` and return the measured throughput, or ``None`` on error."""
        if not url:
            return None
        import requests

        try:
            start = time.monotonic()
            total = 0
            with requests.get(url, stream=True, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                    total += len(chunk)
            return throughput_mbps(total, time.monotonic() - start)
        except requests.RequestException as error:
            log.info("speed test failed", extra={"error": str(error)})
            return None
