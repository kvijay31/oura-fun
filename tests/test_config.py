"""Tests for env config token discovery."""

import os
import pytest
from unittest.mock import patch


def test_tokens_found():
    env = {
        "OURA_TOKEN_KARTIK": "tok_kartik",
        "OURA_TOKEN_PARTNER": "tok_partner",
        "UNRELATED_VAR": "ignored",
    }
    with patch.dict(os.environ, env, clear=False):
        # reimport to pick up patched env
        import importlib
        import oura_fun.config as cfg_mod
        importlib.reload(cfg_mod)
        tokens = cfg_mod.settings.tokens()

    assert tokens.get("kartik") == "tok_kartik"
    assert tokens.get("partner") == "tok_partner"
    assert "unrelated_var" not in tokens


def test_no_tokens_returns_empty():
    # strip any OURA_TOKEN_* from the environment
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("OURA_TOKEN_")}
    with patch.dict(os.environ, clean_env, clear=True):
        import importlib
        import oura_fun.config as cfg_mod
        importlib.reload(cfg_mod)
        tokens = cfg_mod.settings.tokens()

    assert tokens == {}
