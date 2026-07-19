"""Opaque ID generation (docs/API_SPEC.md §1: IDs are opaque strings, not sequential integers)."""

import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
