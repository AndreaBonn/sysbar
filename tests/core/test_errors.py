from sysbar.core.errors import (
    AppError,
    CapabilityError,
    NotFoundError,
    PrivilegedActionError,
    ValidationError,
)


def test_app_error_uses_default_code_when_none_given() -> None:
    error = AppError("boom")
    assert error.message == "boom"
    assert error.code == "INTERNAL_ERROR"


def test_app_error_accepts_explicit_code() -> None:
    error = AppError("boom", code="CUSTOM")
    assert error.code == "CUSTOM"


def test_app_error_message_reaches_exception_str() -> None:
    assert str(AppError("human readable")) == "human readable"


def test_validation_error_has_validation_code() -> None:
    assert ValidationError("bad input").code == "VALIDATION_ERROR"


def test_validation_error_is_app_error() -> None:
    assert isinstance(ValidationError("x"), AppError)


def test_not_found_error_formats_entity_and_identifier() -> None:
    error = NotFoundError("User", "42")
    assert error.message == "User 42 not found"
    assert error.code == "NOT_FOUND"


def test_capability_error_records_capability_name() -> None:
    error = CapabilityError("polkit")
    assert error.capability == "polkit"
    assert error.message == "capability 'polkit' is not available"
    assert error.code == "CAPABILITY_UNAVAILABLE"


def test_privileged_action_error_has_stable_code() -> None:
    assert PrivilegedActionError("pkexec denied").code == "PRIVILEGED_ACTION_FAILED"
