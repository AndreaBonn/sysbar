"""Which clipboard text the palette masks until asked to reveal it."""

from __future__ import annotations

import pytest

from sysbar.services.clipboard.sensitive_text import looks_like_secret, mask


@pytest.mark.parametrize(
    "text",
    [
        "ghp_16CharactersAndThenSomeMore1234",
        "github_pat_11ABCDEFG0abcdefghijklmno",
        "glpat-abcdefghijklmnopqrst",
        "sk-proj-abcdefghijklmnopqrstuvwx",
        "xoxb-1234567890-abcdefghijklmno",
        "AKIAIOSFODNN7EXAMPLE",
        "AIzaSyD-abcdefghijklmnopqrstuvwxyz01",
        "npm_abcdefghijklmnopqrstuvwxyz0123",
    ],
)
def test_known_vendor_prefixes_are_treated_as_secrets(text: str) -> None:
    assert looks_like_secret(text) is True


def test_a_jwt_is_treated_as_a_secret() -> None:
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r"

    assert looks_like_secret(token) is True


def test_a_url_carrying_a_token_is_treated_as_a_secret() -> None:
    assert looks_like_secret("https://api.example.com/v1/items?api_key=abc123") is True


def test_a_url_carrying_a_password_is_treated_as_a_secret() -> None:
    assert looks_like_secret("https://example.com/login?password=hunter2") is True


def test_a_long_opaque_mixed_token_is_treated_as_a_secret() -> None:
    assert looks_like_secret("aB3dE5gH7jK9mN1pQ3rS5tU7wX9zA1cD") is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "hello",
        "Remember to call the bank tomorrow",
        "https://github.com/AndreaBonn/sysbar",
        "sudo apt update && sudo apt upgrade sysbar",
        "/home/bonn/Documenti/progetto/README.md",
    ],
)
def test_ordinary_text_is_not_treated_as_a_secret(text: str) -> None:
    assert looks_like_secret(text) is False


def test_a_long_lowercase_word_is_not_a_secret() -> None:
    """One character class only: no reason to think it was generated."""
    assert looks_like_secret("abcdefghijklmnopqrstuvwxyz") is False


def test_text_with_spaces_is_never_an_opaque_token() -> None:
    assert looks_like_secret("aB3dE5gH7jK9 mN1pQ3rS5tU7wX9zA1cD") is False


def test_a_plain_https_url_is_not_masked_by_the_entropy_rule() -> None:
    long_url = "https://example.com/a/very/long/path/that/keeps/going/and/going"

    assert looks_like_secret(long_url) is False


def test_leading_and_trailing_space_does_not_hide_a_secret() -> None:
    assert looks_like_secret("  ghp_16CharactersAndThenSomeMore1234  ") is True


# --- masking --------------------------------------------------------------


def test_masking_keeps_a_short_prefix_visible() -> None:
    assert mask("ghp_secretvalue").startswith("ghp_")


def test_masking_hides_the_remainder() -> None:
    masked = mask("ghp_secretvalue")

    assert "secretvalue" not in masked


def test_masking_a_very_short_value_reveals_nothing() -> None:
    assert mask("abc") == "•••"


def test_masking_does_not_grow_without_bound() -> None:
    masked = mask("x" * 500)

    assert len(masked) <= 20


def test_masking_collapses_whitespace() -> None:
    assert "\n" not in mask("line one\nline two and a lot more text here")
