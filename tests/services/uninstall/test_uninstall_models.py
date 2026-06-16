from sysbar.services.uninstall.models import Leftover, LeftoverCategory, recoverable_bytes


def _leftover(size: int) -> Leftover:
    return Leftover(category=LeftoverCategory.CACHE, path="/x", size_bytes=size)


def test_recoverable_bytes_sums_leftover_sizes() -> None:
    assert recoverable_bytes([_leftover(100), _leftover(250)]) == 350


def test_recoverable_bytes_empty_is_zero() -> None:
    assert recoverable_bytes([]) == 0
