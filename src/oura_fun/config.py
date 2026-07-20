"""Env config: reads OURA_TOKEN_<PERSON> entries from .env, merged with people_store."""

from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    def tokens(self) -> dict[str, str]:
        """Return {person: token} merging .env variables and the durable people store.

        .env-provided tokens take precedence so local config always wins.
        """
        from oura_fun.people_store import get_tokens as _store_tokens

        result: dict[str, str] = {}

        # Load durable store first (lower priority).
        try:
            result.update(_store_tokens())
        except Exception:
            pass

        # .env / environment variables override the store.
        prefix = "OURA_TOKEN_"
        for key, value in {**dict(os.environ), **self.model_extra}.items():  # type: ignore[arg-type]
            if key.upper().startswith(prefix) and value:
                person = key[len(prefix):].lower()
                result[person] = value

        return result


settings = Settings()
