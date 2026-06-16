"""Raw sensor reading dump, printed by ``sysbar --sensors``."""

from __future__ import annotations


def _dump_temperatures() -> list[str]:
    import psutil

    if not hasattr(psutil, "sensors_temperatures"):
        return ["Temperatures: none reported"]
    readings = psutil.sensors_temperatures()
    if not readings:
        return ["Temperatures: none reported"]
    lines = ["Temperatures:"]
    for chip, entries in readings.items():
        for entry in entries:
            label = entry.label or chip
            lines.append(f"  {chip}/{label}: {entry.current} C")
    return lines


def _dump_fans() -> list[str]:
    import psutil

    if not hasattr(psutil, "sensors_fans"):
        return ["Fans: none reported"]
    readings = psutil.sensors_fans()
    if not readings:
        return ["Fans: none reported"]
    lines = ["Fans:"]
    for chip, entries in readings.items():
        for entry in entries:
            label = entry.label or chip
            lines.append(f"  {chip}/{label}: {entry.current} RPM")
    return lines


def run_sensors_dump() -> str:
    """Return a dump of available temperature/fan sensors for debugging."""
    lines = ["Sysbar sensors dump", ""]
    lines.extend(_dump_temperatures())
    lines.extend(_dump_fans())
    return "\n".join(lines)
