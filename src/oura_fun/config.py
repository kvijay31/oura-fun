"""Env config: reads OURA_TOKEN_<PERSON> entries from .env and the people DB table."""

from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    def tokens(self, include_db: bool = True) -> dict[str, str]:
        """Return {person: token} from OURA_TOKEN_<PERSON> env vars, merged with the DB people table.

        Env vars take precedence over DB entries when both define the same person_id.
        Pass include_db=False to skip the DB lookup (useful during DB bootstrap).
        """
        result: dict[str, str] = {}

        # DB people table — lower priority; read first so env can override
        if include_db:
            try:
                from oura_fun import db as dbmod
                conn = dbmod.connect()
                db_people = dbmod.list_people_from_db(conn)
                conn.close()
                result.update(db_people)
            except Exception:
                pass  # DB not initialised yet or unavailable

        # Env vars — higher priority
        prefix = "OURA_TOKEN_"
        for key, value in {**dict(os.environ), **self.model_extra}.items():  # type: ignore[arg-type]
            if key.upper().startswith(prefix) and value:
                person = key[len(prefix):].lower()
                result[person] = value

        return result


settings = Settings()
