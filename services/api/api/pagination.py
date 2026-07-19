"""Cursor-paginate a query ordered by (sort_column, id) (docs/API_SPEC.md §1)."""

from common.pagination import clamp_limit, decode_cursor, encode_cursor
from sqlalchemy import Select, tuple_
from sqlalchemy.orm import Session


def paginate(session: Session, stmt: Select, model, sort_column, limit: int, cursor: str | None):
    limit = clamp_limit(limit)
    stmt = stmt.order_by(sort_column.asc(), model.id.asc())
    if cursor:
        sort_value, row_id = decode_cursor(cursor)
        stmt = stmt.where(tuple_(sort_column, model.id) > (sort_value, row_id))
    stmt = stmt.limit(limit + 1)

    rows = list(session.execute(stmt).scalars().all())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(getattr(last, sort_column.key), last.id)
    return rows, next_cursor
