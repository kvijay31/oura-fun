"""Verify each OURA_TOKEN_<PERSON> authenticates against the Oura API.

Usage:
    uv run python scripts/check_auth.py
"""

from __future__ import annotations

import sys
import httpx

PERSONAL_INFO_URL = "https://api.ouraring.com/v2/usercollection/personal_info"


def check_token(person: str, token: str) -> bool:
    try:
        resp = httpx.get(
            PERSONAL_INFO_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            email = data.get("email", "<no email>")
            print(f"  [{person}] OK — {email}")
            return True
        elif resp.status_code == 401:
            print(f"  [{person}] FAIL — 401 Unauthorized (token invalid or expired)")
        else:
            print(f"  [{person}] FAIL — HTTP {resp.status_code}: {resp.text[:200]}")
    except httpx.RequestError as exc:
        print(f"  [{person}] ERROR — {exc}")
    return False


def main() -> None:
    import importlib.util, pathlib, sys

    # ensure src is importable when run directly
    src = pathlib.Path(__file__).parent.parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from oura_fun.config import settings

    tokens = settings.tokens()
    if not tokens:
        print(
            "No OURA_TOKEN_<PERSON> variables found.\n"
            "Copy .env.example to .env and fill in your token(s).",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Checking {len(tokens)} token(s)…")
    failures = [p for p, t in tokens.items() if not check_token(p, t)]
    if failures:
        print(f"\n{len(failures)} token(s) failed: {', '.join(failures)}")
        sys.exit(1)
    print("\nAll tokens authenticated successfully.")


if __name__ == "__main__":
    main()
