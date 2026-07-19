"""Pydantic models mirroring docs/API_SPEC.md's resource shapes and conventions."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CameraCreate(BaseModel):
    name: str
    lat: float
    lon: float
    stream_url: str


class CameraUpdate(BaseModel):
    name: str | None = None
    lat: float | None = None
    lon: float | None = None
    stream_url: str | None = None


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    lat: float
    lon: float
    stream_url: str
    status: str
    created_at: datetime


class CameraListOut(BaseModel):
    data: list[CameraOut]
    next_cursor: str | None


class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    camera_id: str
    started_at: datetime
    ended_at: datetime | None


class TrackListOut(BaseModel):
    data: list[TrackOut]
    next_cursor: str | None


class DetectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    track_id: str
    captured_at: datetime
    bounding_box: dict
    confidence: float


class DetectionListOut(BaseModel):
    data: list[DetectionOut]
    next_cursor: str | None
