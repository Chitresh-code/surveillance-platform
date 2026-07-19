from datetime import datetime

from common.ids import new_id
from common.models import Camera, Track
from common.pagination import DEFAULT_LIMIT
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.errors import APIError
from api.pagination import paginate
from api.schemas import CameraCreate, CameraListOut, CameraOut, CameraUpdate, TrackListOut

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _get_camera_or_404(session: Session, camera_id: str) -> Camera:
    camera = session.get(Camera, camera_id)
    if camera is None:
        raise APIError(404, "camera_not_found", f"No camera with id {camera_id}.")
    return camera


@router.post("", response_model=CameraOut, status_code=201)
def create_camera(body: CameraCreate, session: Session = Depends(get_db)) -> Camera:
    camera = Camera(id=new_id("cam"), status="idle", **body.model_dump())
    session.add(camera)
    session.flush()
    return camera


@router.get("", response_model=CameraListOut)
def list_cameras(limit: int = DEFAULT_LIMIT, cursor: str | None = None, session: Session = Depends(get_db)) -> dict:
    rows, next_cursor = paginate(session, select(Camera), Camera, Camera.created_at, limit, cursor)
    return {"data": rows, "next_cursor": next_cursor}


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: str, session: Session = Depends(get_db)) -> Camera:
    return _get_camera_or_404(session, camera_id)


@router.patch("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: str, body: CameraUpdate, session: Session = Depends(get_db)) -> Camera:
    camera = _get_camera_or_404(session, camera_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    session.flush()
    return camera


@router.delete("/{camera_id}", status_code=204)
def delete_camera(camera_id: str, session: Session = Depends(get_db)) -> None:
    camera = _get_camera_or_404(session, camera_id)
    has_tracks = session.execute(select(Track.id).where(Track.camera_id == camera_id).limit(1)).first()
    if has_tracks:
        raise APIError(409, "camera_has_tracks", f"Camera {camera_id} has recorded tracks and can't be deleted.")
    session.delete(camera)


@router.post("/{camera_id}/stream/start", response_model=CameraOut)
def start_stream(camera_id: str, session: Session = Depends(get_db)) -> Camera:
    camera = _get_camera_or_404(session, camera_id)
    camera.status = "streaming"
    session.flush()
    return camera


@router.post("/{camera_id}/stream/stop", response_model=CameraOut)
def stop_stream(camera_id: str, session: Session = Depends(get_db)) -> Camera:
    camera = _get_camera_or_404(session, camera_id)
    camera.status = "idle"
    session.flush()
    return camera


@router.get("/{camera_id}/tracks", response_model=TrackListOut)
def list_camera_tracks(
    camera_id: str,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    session: Session = Depends(get_db),
) -> dict:
    _get_camera_or_404(session, camera_id)
    stmt = select(Track).where(Track.camera_id == camera_id)
    if from_ is not None:
        stmt = stmt.where(Track.started_at >= from_)
    if to is not None:
        stmt = stmt.where(Track.started_at <= to)
    rows, next_cursor = paginate(session, stmt, Track, Track.started_at, limit, cursor)
    return {"data": rows, "next_cursor": next_cursor}
