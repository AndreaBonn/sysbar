"""The command-line front end: parsing, exit codes and what it does not import."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from sysbar import __main__
from sysbar.app.commands.catalogue import CATALOGUE


def test_action_is_optional_so_a_bare_launch_still_parses() -> None:
    args = __main__.build_parser().parse_args([])

    assert args.action is None
    assert args.argument is None


def test_a_known_action_parses() -> None:
    args = __main__.build_parser().parse_args(["open-panel"])

    assert args.action == "open-panel"


def test_an_action_argument_parses() -> None:
    args = __main__.build_parser().parse_args(["activate-scene", "focus"])

    assert args.action == "activate-scene"
    assert args.argument == "focus"


def test_an_unknown_action_exits_with_the_usage_code() -> None:
    with pytest.raises(SystemExit) as exit_info:
        __main__.build_parser().parse_args(["definitely-not-a-command"])

    assert exit_info.value.code == __main__.EXIT_BAD_USAGE


def test_the_error_for_an_unknown_action_lists_the_valid_ones(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        __main__.build_parser().parse_args(["nope"])

    assert "open-panel" in capsys.readouterr().err


def test_the_parser_accepts_every_catalogue_command() -> None:
    parser = __main__.build_parser()

    for command in CATALOGUE:
        assert parser.parse_args([command.id.value]).action == command.id.value


# --- --list-actions -------------------------------------------------------


def test_list_actions_prints_every_command(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    mocker.patch("sysbar.core.logging_setup.configure_logging")

    assert __main__.main(["--list-actions"]) == __main__.EXIT_OK

    printed = capsys.readouterr().out
    for command in CATALOGUE:
        assert command.id.value in printed


def test_list_actions_includes_the_titles() -> None:
    listing = __main__.format_action_list()

    assert CATALOGUE[0].title in listing


# --- sending --------------------------------------------------------------


def test_sending_a_command_returns_zero_on_success(mocker: MockerFixture) -> None:
    remote = mocker.patch("sysbar.app.remote.DBusRemoteControl")

    assert __main__.send_action("open-panel", None) == __main__.EXIT_OK
    remote.return_value.activate.assert_called_once_with("open-panel", None)


def test_sending_forwards_the_argument(mocker: MockerFixture) -> None:
    remote = mocker.patch("sysbar.app.remote.DBusRemoteControl")

    __main__.send_action("activate-scene", "focus")

    remote.return_value.activate.assert_called_once_with("activate-scene", "focus")


def test_sending_to_a_stopped_instance_reports_and_returns_one(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    from sysbar.app.remote import NotRunningError

    remote = mocker.patch("sysbar.app.remote.DBusRemoteControl")
    remote.return_value.activate.side_effect = NotRunningError("io.github.AndreaBonn.Sysbar")

    assert __main__.send_action("open-panel", None) == __main__.EXIT_NOT_RUNNING
    assert "not running" in capsys.readouterr().err


def test_a_command_never_starts_the_application(mocker: MockerFixture) -> None:
    """A script sending a command must not spawn a tray daemon as a side effect."""
    mocker.patch("sysbar.core.logging_setup.configure_logging")
    mocker.patch("sysbar.app.remote.DBusRemoteControl")
    identity = mocker.patch("sysbar.__main__.configure_window_identity")

    assert __main__.main(["open-panel"]) == __main__.EXIT_OK
    identity.assert_not_called()
