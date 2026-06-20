from __future__ import annotations

from sysbar.services.quick_toggles.desktop_toggles import ColorSchemeToggle, DoNotDisturbToggle


class FakeStore:
    def __init__(
        self, booleans: dict[str, bool] | None = None, strings: dict[str, str] | None = None
    ) -> None:
        self._booleans = booleans or {}
        self._strings = strings or {}

    def get_boolean(self, key: str) -> bool:
        return self._booleans.get(key, False)

    def set_boolean(self, key: str, value: bool) -> None:
        self._booleans[key] = value

    def get_string(self, key: str) -> str:
        return self._strings.get(key, "")

    def set_string(self, key: str, value: str) -> None:
        self._strings[key] = value


# --------------------------------------------------------------------------- #
# Do Not Disturb — banners on means DND off
# --------------------------------------------------------------------------- #


def test_dnd_active_when_banners_off() -> None:
    toggle = DoNotDisturbToggle(FakeStore(booleans={"show-banners": False}))
    assert toggle.is_active() is True


def test_dnd_inactive_when_banners_on() -> None:
    toggle = DoNotDisturbToggle(FakeStore(booleans={"show-banners": True}))
    assert toggle.is_active() is False


def test_toggle_dnd_turns_banners_off() -> None:
    store = FakeStore(booleans={"show-banners": True})
    DoNotDisturbToggle(store).toggle()
    assert store.get_boolean("show-banners") is False


def test_toggle_dnd_turns_banners_back_on() -> None:
    store = FakeStore(booleans={"show-banners": False})
    DoNotDisturbToggle(store).toggle()
    assert store.get_boolean("show-banners") is True


# --------------------------------------------------------------------------- #
# Colour scheme — prefer-dark vs default
# --------------------------------------------------------------------------- #


def test_is_dark_true_for_prefer_dark() -> None:
    toggle = ColorSchemeToggle(FakeStore(strings={"color-scheme": "prefer-dark"}))
    assert toggle.is_dark() is True


def test_is_dark_false_for_default() -> None:
    toggle = ColorSchemeToggle(FakeStore(strings={"color-scheme": "default"}))
    assert toggle.is_dark() is False


def test_toggle_enables_dark_from_default() -> None:
    store = FakeStore(strings={"color-scheme": "default"})
    ColorSchemeToggle(store).toggle()
    assert store.get_string("color-scheme") == "prefer-dark"


def test_toggle_returns_to_default_from_dark() -> None:
    store = FakeStore(strings={"color-scheme": "prefer-dark"})
    ColorSchemeToggle(store).toggle()
    assert store.get_string("color-scheme") == "default"
