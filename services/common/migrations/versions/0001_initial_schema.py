"""Initial schema: cameras, tracks, detections

Revision ID: 0001
Revises:
Create Date: 2026-07-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cameras",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lon", sa.Float, nullable=False),
        sa.Column("stream_url", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="idle"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "tracks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("camera_id", sa.String, sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tracks_camera_id", "tracks", ["camera_id"])

    op.create_table(
        "detections",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("track_id", sa.String, sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bounding_box", sa.JSON, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("frame_path", sa.String, nullable=True),
    )
    op.create_index("ix_detections_track_id", "detections", ["track_id"])


def downgrade() -> None:
    op.drop_index("ix_detections_track_id", table_name="detections")
    op.drop_table("detections")
    op.drop_index("ix_tracks_camera_id", table_name="tracks")
    op.drop_table("tracks")
    op.drop_table("cameras")
