from datetime import datetime, timezone

import cv2
import numpy as np
from common.db import session_scope
from common.models import Track

from detection.worker import DetectionWorker


class _FakeBoxes:
    def cpu(self):
        return self

    def numpy(self):
        return self


class _FakeResult:
    def __init__(self):
        self.boxes = _FakeBoxes()


def _fake_model():
    def model(frame, classes=None, verbose=False):
        return [_FakeResult()]

    return model


class _FakeTracker:
    def __init__(self):
        self.next_rows: list[list[float]] = []

    def update(self, boxes, frame):
        return np.array(self.next_rows, dtype=np.float32)


def _frame_fields(captured_at: datetime) -> dict:
    ok, buf = cv2.imencode(".jpg", np.zeros((20, 20, 3), dtype=np.uint8))
    assert ok
    return {b"captured_at": captured_at.isoformat().encode(), b"jpeg": buf.tobytes()}


def test_worker_opens_and_closes_a_track_as_the_tracker_id_appears_and_disappears(tmp_path):
    redis_client = _NoopRedis()
    worker = DetectionWorker(
        camera_id="cam_test",
        model=_fake_model(),
        redis_client=redis_client,
        frame_store_dir=str(tmp_path),
        consumer_name="test-worker",
    )
    worker.tracker = _FakeTracker()

    t1 = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)
    worker.tracker.next_rows = [[0.0, 0.0, 10.0, 10.0, 1.0, 0.9, 0.0, 0.0]]
    worker._process_message(b"1-1", _frame_fields(t1))

    assert list(worker._local_to_db_track) == [1]
    track_id = worker._local_to_db_track[1]
    with session_scope() as session:
        track = session.get(Track, track_id)
        assert track is not None
        assert track.ended_at is None

    t2 = datetime(2026, 7, 19, 12, 0, 1, tzinfo=timezone.utc)
    worker.tracker.next_rows = [[1.0, 1.0, 11.0, 11.0, 1.0, 0.9, 0.0, 0.0]]
    worker._process_message(b"1-2", _frame_fields(t2))

    assert worker._local_to_db_track[1] == track_id  # same local id reuses the same DB track

    t3 = datetime(2026, 7, 19, 12, 0, 2, tzinfo=timezone.utc)
    worker.tracker.next_rows = []  # person left the frame
    worker._process_message(b"1-3", _frame_fields(t3))

    assert worker._local_to_db_track == {}
    with session_scope() as session:
        track = session.get(Track, track_id)
        # sqlite (test-only; production is Postgres per ADR-0002) doesn't round-trip tzinfo
        assert track.ended_at.replace(tzinfo=timezone.utc) == t3

    assert redis_client.published == [("tracks:ready", {"track_id": track_id})]


class _NoopRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def xack(self, *args, **kwargs) -> None:
        pass

    def xadd(self, stream_key: str, fields: dict) -> None:
        self.published.append((stream_key, fields))
