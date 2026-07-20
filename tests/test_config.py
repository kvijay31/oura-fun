"""Tests for env config token discovery."""

from unittest.mock import patch

from oura_fun.config import Settings


def _settings(**extra_env):
    with patch.dict("os.environ", extra_env, clear=True):
        return Settings(_env_file=None)


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
        # Patch people_store to return empty so no DB file needed.
        with patch("oura_fun.config.Settings.tokens", wraps=None):
            pass
        with patch("oura_fun.people_store.get_tokens", return_value={}):
            tokens = Settings(_env_file=None).tokens()

    assert tokens == {}


def test_store_tokens_merged():
    """Tokens from the people store appear when not in .env."""
    store = {"alice": "tok_alice", "bob": "tok_bob"}
    with patch.dict("os.environ", {}, clear=True):
        with patch("oura_fun.people_store.get_tokens", return_value=store):
            tokens = Settings(_env_file=None).tokens()

    assert tokens == {"alice": "tok_alice", "bob": "tok_bob"}


def test_env_overrides_store():
    """.env token takes precedence over the store token for the same person."""
    store = {"kartik": "tok_from_store", "partner": "tok_partner_store"}
    env = {"OURA_TOKEN_KARTIK": "tok_from_env"}
    with patch.dict("os.environ", env, clear=True):
        with patch("oura_fun.people_store.get_tokens", return_value=store):
            tokens = Settings(_env_file=None).tokens()

    assert tokens["kartik"] == "tok_from_env"
    assert tokens["partner"] == "tok_partner_store"


def test_store_failure_is_silent():
    """If the people store raises, tokens() still returns .env tokens."""
    env = {"OURA_TOKEN_KARTIK": "tok_kartik"}
    with patch.dict("os.environ", env, clear=True):
        with patch("oura_fun.people_store.get_tokens", side_effect=RuntimeError("db gone")):
            tokens = Settings(_env_file=None).tokens()

    assert tokens == {"kartik": "tok_kartik"}
