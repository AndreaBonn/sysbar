from sysbar.services.update_service import is_newer, parse_version


def test_parse_version_strips_v_prefix() -> None:
    assert parse_version("v1.2.3") == (1, 2, 3)


def test_parse_version_plain() -> None:
    assert parse_version("0.1.0") == (0, 1, 0)


def test_is_newer_detects_higher_patch() -> None:
    assert is_newer("0.1.0", "0.1.1") is True


def test_is_newer_detects_higher_minor() -> None:
    assert is_newer("0.1.5", "0.2.0") is True


def test_is_newer_false_for_same_version() -> None:
    assert is_newer("1.0.0", "1.0.0") is False


def test_is_newer_false_for_older() -> None:
    assert is_newer("2.0.0", "1.9.9") is False


def test_is_newer_handles_v_prefix_on_both() -> None:
    assert is_newer("v1.0.0", "v1.0.1") is True
