from datetime import datetime, timezone

import cv2
import numpy as np
from common.db import session_scope
from common.ids import new_id
from common.models import Camera, Detection, Identity, Sighting, Track
from sqlalchemy import select

from reid.worker import ReidWorker


class _FakeEncoder:
    def __init__(self):
        self.next_embedding = np.array([1.0, 0.0], dtype=np.float32)

    def __call__(self, image, dets):
        return [self.next_embedding]


class _FakeRedis:
    def xack(self, *args, **kwargs) -> None:
        pass


def _make_track_with_detection(tmp_path, confidence: float = 0.9) -> str:
    camera_id = new_id("cam")
    track_id = new_id("trk")
    detection_id = new_id("det")
    crop_path = str(tmp_path / f"{detection_id}.jpg")
    cv2.imwrite(crop_path, np.zeros((20, 20, 3), dtype=np.uint8))

    now = datetime.now(timezone.utc)
    with session_scope() as session:
        session.add(Camera(id=camera_id, name="Test Cam", lat=0.0, lon=0.0, stream_url="rtsp://x", status="idle"))
        session.add(Track(id=track_id, camera_id=camera_id, started_at=now, ended_at=now))
        session.add(
            Detection(
                id=detection_id,
                track_id=track_id,
                captured_at=now,
                bounding_box={"x": 0, "y": 0, "w": 20, "h": 20},
                confidence=confidence,
                frame_path=crop_path,
            )
        )
    return track_id


def _sighting_for(track_id: str) -> Sighting:
    with session_scope() as session:
        return session.execute(select(Sighting).where(Sighting.track_id == track_id)).scalar_one()


def test_worker_creates_a_new_identity_when_nothing_matches(tmp_path):
    worker = ReidWorker(encoder=_FakeEncoder(), redis_client=_FakeRedis(), consumer_name="test", match_threshold=0.6)
    track_id = _make_track_with_detection(tmp_path)

    worker._process_message(b"1-1", {b"track_id": track_id.encode()})

    sighting = _sighting_for(track_id)
    assert sighting.match_confidence == 1.0
    with session_scope() as session:
        assert session.get(Identity, sighting.identity_id) is not None


def test_worker_matches_an_existing_identity_when_embedding_is_close(tmp_path):
    encoder = _FakeEncoder()
    worker = ReidWorker(encoder=encoder, redis_client=_FakeRedis(), consumer_name="test", match_threshold=0.6)

    track_1 = _make_track_with_detection(tmp_path)
    worker._process_message(b"1-1", {b"track_id": track_1.encode()})

    track_2 = _make_track_with_detection(tmp_path)
    encoder.next_embedding = np.array([0.99, 0.01], dtype=np.float32)
    worker._process_message(b"1-2", {b"track_id": track_2.encode()})

    assert _sighting_for(track_1).identity_id == _sighting_for(track_2).identity_id


def test_worker_creates_a_second_identity_when_embedding_is_far(tmp_path):
    encoder = _FakeEncoder()
    worker = ReidWorker(encoder=encoder, redis_client=_FakeRedis(), consumer_name="test", match_threshold=0.6)

    track_1 = _make_track_with_detection(tmp_path)
    worker._process_message(b"1-1", {b"track_id": track_1.encode()})

    track_2 = _make_track_with_detection(tmp_path)
    encoder.next_embedding = np.array([0.0, 1.0], dtype=np.float32)
    worker._process_message(b"1-2", {b"track_id": track_2.encode()})

    assert _sighting_for(track_1).identity_id != _sighting_for(track_2).identity_id
