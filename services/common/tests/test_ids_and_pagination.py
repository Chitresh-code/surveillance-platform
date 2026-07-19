from datetime import datetime, timezone

from common.ids import new_id
from common.pagination import clamp_limit, decode_cursor, encode_cursor


def test_new_id_uses_prefix_and_is_unique():
    a = new_id("cam")
    b = new_id("cam")
    assert a.startswith("cam_")
    assert a != b


def test_cursor_round_trips():
    when = datetime(2026, 7, 19, 14, 2, 31, tzinfo=timezone.utc)
    cursor = encode_cursor(when, "trk_abc123")
    assert decode_cursor(cursor) == (when, "trk_abc123")


def test_clamp_limit_bounds_to_valid_range():
    assert clamp_limit(0) == 1
    assert clamp_limit(50) == 50
    assert clamp_limit(500) == 200
