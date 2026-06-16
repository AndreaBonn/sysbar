import pytest
import requests

from sysbar.services.metrics import speedtest
from sysbar.services.metrics.speedtest import SpeedTestService, throughput_mbps


class _FakeResponse:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int) -> list[bytes]:
        return self._chunks


class _FakeClock:
    def __init__(self, times: list[float]) -> None:
        self._times = iter(times)

    def monotonic(self) -> float:
        return next(self._times)


def test_throughput_one_megabyte_per_second() -> None:
    # 1_000_000 bytes in 1 s = 8 Mbit/s
    assert throughput_mbps(1_000_000, 1.0) == 8.0


def test_throughput_scales_with_time() -> None:
    assert throughput_mbps(1_000_000, 2.0) == 4.0


def test_throughput_zero_seconds_is_safe() -> None:
    assert throughput_mbps(1_000_000, 0.0) == 0.0


def test_throughput_zero_bytes() -> None:
    assert throughput_mbps(0, 1.0) == 0.0


def test_download_mbps_empty_url_returns_none() -> None:
    assert SpeedTestService().download_mbps("") is None


def test_download_mbps_measures_throughput(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(speedtest, "time", _FakeClock([0.0, 2.0]))
    monkeypatch.setattr(
        requests, "get", lambda _url, stream, timeout: _FakeResponse([b"x" * 600, b"y" * 400])
    )
    # 1000 bytes over 2 s = (1000 * 8) / (2 * 1_000_000) Mbit/s
    assert SpeedTestService().download_mbps("http://host/file") == 0.004


def test_download_mbps_returns_none_on_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_url: str, stream: bool, timeout: int) -> _FakeResponse:
        raise requests.RequestException("connection reset")

    monkeypatch.setattr(requests, "get", _boom)
    assert SpeedTestService().download_mbps("http://host/file") is None
