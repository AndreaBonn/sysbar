import pytest
import requests

from sysbar.services.update_service import UpdateInfo, UpdateService, is_newer, parse_version


class _Response:
    def __init__(self, payload: object, json_error: bool = False) -> None:
        self._payload = payload
        self._json_error = json_error

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        if self._json_error:
            raise ValueError("invalid json")
        return self._payload


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


def test_check_returns_update_when_release_is_newer(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"tag_name": "v2.0.0", "html_url": "https://example.com/r/2.0.0"}
    monkeypatch.setattr(requests, "get", lambda _url, timeout: _Response(payload))
    result = UpdateService(current_version="1.0.0").check()
    assert result == UpdateInfo(version="v2.0.0", url="https://example.com/r/2.0.0")


def test_check_returns_none_when_release_not_newer(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"tag_name": "v0.0.1", "html_url": "x"}
    monkeypatch.setattr(requests, "get", lambda _url, timeout: _Response(payload))
    assert UpdateService(current_version="1.0.0").check() is None


def test_check_returns_none_when_tag_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(requests, "get", lambda _url, timeout: _Response({}))
    assert UpdateService(current_version="1.0.0").check() is None


def test_check_returns_none_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_url: str, timeout: int) -> _Response:
        raise requests.RequestException("offline")

    monkeypatch.setattr(requests, "get", _boom)
    assert UpdateService(current_version="1.0.0").check() is None


def test_check_returns_none_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(requests, "get", lambda _url, timeout: _Response(None, json_error=True))
    assert UpdateService(current_version="1.0.0").check() is None
