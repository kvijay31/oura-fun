"""Env config: reads OURA_TOKEN_<PERSON> entries from .env."""

from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    def tokens(self) -> dict[str, str]:
        """Return {person: token} for every OURA_TOKEN_<PERSON> variable found."""
        result: dict[str, str] = {}
        prefix = "OURA_TOKEN_"
        for key, value in {**dict(os.environ), **self.model_extra}.items():  # type: ignore[arg-type]
            if key.upper().startswith(prefix) and value:
                person = key[len(prefix):].lower()
                result[person] = value
        return result


settings = Settings()
