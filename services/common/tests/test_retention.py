from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session, sessionmaker

from common.db import make_engine
from common.ids import new_id
from common.models import Base, Camera, Detection, Identity, Sighting, Track
from common.retention import delete_identity, gc_expired

NOW = datetime(2026, 7, 19, tzinfo=timezone.utc)
OLD = NOW - timedelta(days=200)
RECENT = NOW - timedelta(days=1)


@pytest.fixture
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def _add_camera(session: Session) -> Camera:
    camera = Camera(id=new_id("cam"), name="Lobby", lat=0.0, lon=0.0, stream_url="0")
    session.add(camera)
    return camera


def _add_matched_track(session: Session, camera: Camera, when: datetime, frame_path: str | None = None) -> tuple[Track, Identity]:
    track = Track(id=new_id("trk"), camera_id=camera.id, started_at=when)
    session.add(track)
    detection = Detection(id=new_id("det"), track_id=track.id, captured_at=when, bounding_box={}, confidence=0.9, frame_path=frame_path)
    session.add(detection)
    identity = Identity(id=new_id("idn"), first_seen=when, last_seen=when, embedding=[0.1])
    session.add(identity)
    sighting = Sighting(id=new_id("sgt"), identity_id=identity.id, track_id=track.id, camera_id=camera.id, seen_at=when, match_confidence=0.9)
    session.add(sighting)
    session.flush()
    return track, identity


def test_delete_identity_cascades_to_track_and_detection(session, tmp_path):
    camera = _add_camera(session)
    frame_path = tmp_path / "det.jpg"
    frame_path.write_bytes(b"jpeg")
    track, identity = _add_matched_track(session, camera, NOW, frame_path=str(frame_path))
    session.flush()

    stats = delete_identity(session, identity)
    session.flush()

    assert stats.identities == 1
    assert stats.tracks == 1
    assert stats.sightings == 1
    assert stats.detections == 1
    assert session.get(Identity, identity.id) is None
    assert session.get(Track, track.id) is None
    assert not frame_path.exists()


def test_gc_expired_deletes_stale_identity_but_keeps_recent(session):
    camera = _add_camera(session)
    _, stale_identity = _add_matched_track(session, camera, OLD)
    _, fresh_identity = _add_matched_track(session, camera, RECENT)
    session.flush()

    stats = gc_expired(session, cutoff=NOW - timedelta(days=90))
    session.flush()

    assert stats.identities == 1
    assert session.get(Identity, stale_identity.id) is None
    assert session.get(Identity, fresh_identity.id) is not None


def test_gc_expired_deletes_unmatched_stale_track():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        camera = _add_camera(session)
        stale_track = Track(id=new_id("trk"), camera_id=camera.id, started_at=OLD)
        fresh_track = Track(id=new_id("trk"), camera_id=camera.id, started_at=RECENT)
        session.add_all([stale_track, fresh_track])
        session.flush()

        stats = gc_expired(session, cutoff=NOW - timedelta(days=90))
        session.flush()

        assert stats.tracks == 1
        assert session.get(Track, stale_track.id) is None
        assert session.get(Track, fresh_track.id) is not None
