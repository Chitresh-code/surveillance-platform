"""Pipeline/replay tests (docs/TESTING.md layer 3): the real YOLO detector, BYTETracker,
and ReID encoder, run end to end instead of the fakes services/detection/tests and
services/reid/tests deliberately use. The point (docs/TESTING.md §2) is catching a broken
*model* integration — a library API change, a bad asset download, a shape mismatch — not
broken glue code, which the mocked unit test layer already covers.

No real footage is used (docs/TESTING.md §3: fixtures must be synthetic or documented
consent, and small): frames are generated in-process with numpy, not checked into the
repo. That means these tests can't assert a real person gets detected in a synthetic
frame — nothing here trains or fine-tunes the model, and asserting a specific accuracy
outcome is explicitly out of scope for this suite (docs/TESTING.md §5). What they assert
instead is that the real model pipeline runs to completion without crashing on both
plausible input (random noise: zero detections, a legitimate and deterministic outcome)
and implausible input (a corrupt frame), and that a closed track's real embedding really
flows through the real matcher into a real Sighting/Identity.
"""

from datetime import datetime, timezone

import cv2
import numpy as np

CAPTURED_AT = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)


class _NoopRedis:
    def xack(self, *args, **kwargs) -> None:
        pass

    def xadd(self, *args, **kwargs) -> None:
        pass

    def publish(self, *args, **kwargs) -> None:
        pass


def _jpeg_fields(frame: np.ndarray, captured_at: datetime = CAPTURED_AT) -> dict:
    ok, buf = cv2.imencode(".jpg", frame)
    assert ok
    return {b"captured_at": captured_at.isoformat().encode(), b"jpeg": buf.tobytes()}


def test_detection_worker_runs_the_real_model_without_crashing(tmp_path):
    from detection.worker import DetectionWorker
    from ultralytics import YOLO

    model = YOLO("yolov8n.pt")
    worker = DetectionWorker(
        camera_id="cam_replay",
        model=model,
        redis_client=_NoopRedis(),
        frame_store_dir=str(tmp_path),
        consumer_name="replay-test",
    )

    rng = np.random.default_rng(0)
    for i in range(3):
        frame = rng.integers(0, 255, (240, 320, 3), dtype=np.uint8)
        worker._process_message(f"{i}-1".encode(), _jpeg_fields(frame))

    # Random noise contains nothing YOLOv8n recognizes as a person — zero open tracks
    # is the correct, deterministic outcome here, not a weakened assertion (docs/TESTING.md
    # §5 explicitly rules out asserting a specific detection-accuracy outcome; this asserts
    # the real model+tracker ran to completion and produced a well-formed, empty result).
    assert worker._local_to_db_track == {}

    # A corrupt frame must not take down the worker (docs/CODING_STANDARDS.md §5).
    worker._process_message(b"corrupt-1", {b"captured_at": CAPTURED_AT.isoformat().encode(), b"jpeg": b"not-a-jpeg"})


def test_reid_embedder_runs_the_real_model_without_crashing(tmp_path):
    from reid.embedder import build_encoder, embed_crop

    encoder = build_encoder()
    crop = np.random.default_rng(1).integers(0, 255, (128, 64, 3), dtype=np.uint8)
    crop_path = tmp_path / "crop.jpg"
    cv2.imwrite(str(crop_path), crop)

    image = cv2.imread(str(crop_path))
    embedding = embed_crop(encoder, image)

    assert embedding is not None
    assert embedding.shape[0] > 0


def test_reid_worker_runs_the_real_model_end_to_end_from_a_closed_track(tmp_path):
    from common.db import session_scope
    from common.ids import new_id
    from common.models import Camera, Detection, Identity, Sighting, Track
    from reid.embedder import build_encoder
    from reid.worker import ReidWorker

    crop = np.random.default_rng(2).integers(0, 255, (128, 64, 3), dtype=np.uint8)
    crop_path = tmp_path / "crop.jpg"
    cv2.imwrite(str(crop_path), crop)

    with session_scope() as session:
        camera = Camera(id=new_id("cam"), name="Replay Camera", lat=0.0, lon=0.0, stream_url="0")
        session.add(camera)
        track = Track(id=new_id("trk"), camera_id=camera.id, started_at=CAPTURED_AT, ended_at=CAPTURED_AT)
        session.add(track)
        session.add(
            Detection(
                id=new_id("det"),
                track_id=track.id,
                captured_at=CAPTURED_AT,
                bounding_box={"x": 0, "y": 0, "w": 64, "h": 128},
                confidence=0.9,
                frame_path=str(crop_path),
            )
        )
        track_id = track.id

    worker = ReidWorker(encoder=build_encoder(), redis_client=_NoopRedis(), consumer_name="replay-test")
    worker._process_message(b"1-1", {b"track_id": track_id.encode()})

    with session_scope() as session:
        sightings = session.query(Sighting).filter_by(track_id=track_id).all()
        assert len(sightings) == 1
        assert sightings[0].match_confidence == 1.0  # first sighting: a new identity, no prior match

        identity = session.get(Identity, sightings[0].identity_id)
        assert identity is not None
        assert len(identity.embedding) > 0
