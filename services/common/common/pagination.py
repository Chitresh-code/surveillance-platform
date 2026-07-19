"""Cursor pagination helpers (docs/API_SPEC.md §1: limit/cursor, next_cursor null at the end).

Rows are ordered by (sort_time, id) and the cursor opaquely encodes the last row
returned, so a page boundary survives inserts that land elsewhere in the ordering.
"""

import base64
import json
from datetime import datetime

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def encode_cursor(sort_time: datetime, row_id: str) -> str:
    payload = json.dumps([sort_time.isoformat(), row_id])
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    sort_time_iso, row_id = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(sort_time_iso), row_id


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))
