from sysbar.services.shelf.shake_detector import ShakeDetector


def _detector() -> ShakeDetector:
    return ShakeDetector(min_move=8.0, window_seconds=0.6, required_reversals=4)


def test_unidirectional_motion_is_not_a_shake() -> None:
    detector = _detector()
    detected = [detector.feed(20.0, t * 0.05) for t in range(10)]
    assert not any(detected)


def test_small_moves_below_threshold_ignored() -> None:
    detector = _detector()
    signs = [10.0, -10.0, 10.0, -10.0]
    # Interleave sub-threshold jitter; it must not count as reversals.
    detected = []
    for i, dx in enumerate(signs):
        detected.append(detector.feed(2.0, i * 0.05))  # jitter, ignored
        detected.append(detector.feed(dx, i * 0.05 + 0.01))
    assert detected.count(True) <= 1


def test_rapid_reversals_within_window_trigger_shake() -> None:
    detector = _detector()
    deltas = [30.0, -30.0, 30.0, -30.0, 30.0]
    results = [detector.feed(dx, i * 0.05) for i, dx in enumerate(deltas)]
    assert True in results


def test_reversals_outside_window_do_not_trigger() -> None:
    detector = _detector()
    # Reversals spaced 0.3s apart: only ~2 fit in a 0.6s window, below the 4 required.
    deltas = [30.0, -30.0, 30.0, -30.0, 30.0, -30.0]
    results = [detector.feed(dx, i * 0.3) for i, dx in enumerate(deltas)]
    assert True not in results


def test_reset_clears_state() -> None:
    detector = _detector()
    detector.feed(30.0, 0.0)
    detector.feed(-30.0, 0.05)
    detector.reset()
    # After reset, a single sample cannot have accumulated reversals.
    assert detector.feed(30.0, 0.1) is False
