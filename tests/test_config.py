"""Tests for env config token discovery."""

from unittest.mock import patch

from oura_fun.config import Settings


def test_tokens_found():
    env = {
        "OURA_TOKEN_KARTIK": "tok_kartik",
        "OURA_TOKEN_PARTNER": "tok_partner",
        "UNRELATED_VAR": "ignored",
    }
    with patch.dict("os.environ", env, clear=True):
        tokens = Settings(_env_file=None).tokens()

    assert tokens.get("kartik") == "tok_kartik"
    assert tokens.get("partner") == "tok_partner"
    assert "unrelated_var" not in tokens


def test_no_tokens_returns_empty():
    with patch.dict("os.environ", {}, clear=True):
        tokens = Settings(_env_file=None).tokens()

    assert tokens == {}
