"""Identities and sightings

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identities",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("embedding", sa.JSON, nullable=False),
    )

    op.create_table(
        "sightings",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("identity_id", sa.String, sa.ForeignKey("identities.id"), nullable=False),
        sa.Column("track_id", sa.String, sa.ForeignKey("tracks.id"), nullable=False, unique=True),
        sa.Column("camera_id", sa.String, sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_confidence", sa.Float, nullable=False),
    )
    op.create_index("ix_sightings_identity_id", "sightings", ["identity_id"])


def downgrade() -> None:
    op.drop_index("ix_sightings_identity_id", table_name="sightings")
    op.drop_table("sightings")
    op.drop_table("identities")
