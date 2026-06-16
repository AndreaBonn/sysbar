from sysbar.core.capabilities import Capabilities


def test_has_returns_false_before_refresh() -> None:
    caps = Capabilities(detectors={"session_x11": lambda: True})
    assert caps.has("session_x11") is False


def test_refresh_reflects_detector_results() -> None:
    caps = Capabilities(detectors={"session_x11": lambda: True, "polkit": lambda: False})
    caps.refresh()
    assert caps.has("session_x11") is True
    assert caps.has("polkit") is False


def test_refresh_emits_changed_when_state_flips() -> None:
    flag = {"value": True}
    caps = Capabilities(detectors={"sensors": lambda: flag["value"]})
    seen: list[bool] = []
    caps.connect("changed", lambda _obj: seen.append(True))

    caps.refresh()  # initial all-False -> True: flip
    flag["value"] = False
    caps.refresh()  # True -> False: flip

    assert len(seen) == 2


def test_refresh_does_not_emit_when_state_stable() -> None:
    caps = Capabilities(detectors={"sensors": lambda: True})
    seen: list[bool] = []
    caps.connect("changed", lambda _obj: seen.append(True))

    caps.refresh()
    caps.refresh()

    assert len(seen) == 1


def test_failing_detector_is_treated_as_unavailable() -> None:
    def boom() -> bool:
        raise RuntimeError("probe failed")

    caps = Capabilities(detectors={"upower": boom})
    caps.refresh()
    assert caps.has("upower") is False


def test_unknown_capability_reports_false() -> None:
    caps = Capabilities(detectors={"sensors": lambda: True})
    caps.refresh()
    assert caps.has("does_not_exist") is False
