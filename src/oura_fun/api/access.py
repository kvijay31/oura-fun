"""Access-control model for F9.5.

Decision: friends see score-only standings (day + score); household owners see full
raw biometric data.

Role assignment rules (checked in order):
  1. viewer_id absent (local browser, no param) → OWNER (trusted local default)
  2. viewer_id == subject_id                    → OWNER (always see your own data)
  3. viewer_id in OURA_OWNERS env var           → OWNER (household member)
  4. OURA_OWNERS not set at all                 → OWNER (all-access local mode)
  5. otherwise                                  → FRIEND (scores/standings only)

OURA_OWNERS: comma-separated list of person IDs that have household (full) access.
Example .env line:  OURA_OWNERS=alice,bob
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any


class Role(str, Enum):
    OWNER = "owner"
    FRIEND = "friend"


# The only fields a FRIEND viewer may see — aggregate score, no raw biometrics
_SCORE_FIELDS = frozenset({"day", "score"})


def _owner_set() -> frozenset[str]:
    raw = os.environ.get("OURA_OWNERS", "")
    return frozenset(p.strip().lower() for p in raw.split(",") if p.strip())


def get_role(viewer_id: str | None, subject_id: str) -> Role:
    """Return the access role for viewer_id looking at subject_id's data."""
    if viewer_id is None:
        return Role.OWNER
    vid = viewer_id.strip().lower()
    sid = subject_id.strip().lower()
    if vid == sid:
        return Role.OWNER
    owners = _owner_set()
    if not owners:
        return Role.OWNER  # OURA_OWNERS unset → local all-access mode
    if vid in owners:
        return Role.OWNER
    return Role.FRIEND


def filter_records(records: list[dict[str, Any]], role: Role) -> list[dict[str, Any]]:
    """Strip raw-biometric fields when the viewer is a FRIEND."""
    if role is Role.OWNER:
        return records
    return [{k: v for k, v in rec.items() if k in _SCORE_FIELDS} for rec in records]
