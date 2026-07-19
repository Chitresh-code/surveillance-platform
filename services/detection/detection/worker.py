"""Per-camera detection worker: consumes the frame queue, runs the detector, writes results.

A bad frame must not take down the worker (docs/CODING_STANDARDS.md §5) since one
malformed frame is not a reason to drop a camera's whole session.
"""

import logging
import threading
from datetime import datetime

import cv2
import numpy as np
import redis
from common.db import session_scope
from common.ids import new_id
from common.models import Detection

from detection.boxes import run_person_detection
from detection.storage import crop_path, save_crop

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "detection-workers"
BLOCK_MS = 2000


def decode_jpeg(jpeg_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


class DetectionWorker:
    def __init__(
        self,
        camera_id: str,
        model,
        redis_client: redis.Redis,
        frame_store_dir: str,
        consumer_name: str,
        min_confidence: float = 0.5,
    ) -> None:
        self.camera_id = camera_id
        self.stream_key = f"frames:{camera_id}"
        self.model = model
        self.redis_client = redis_client
        self.frame_store_dir = frame_store_dir
        self.consumer_name = consumer_name
        self.min_confidence = min_confidence
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        try:
            self.redis_client.xgroup_create(self.stream_key, CONSUMER_GROUP, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=10)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            response = self.redis_client.xreadgroup(
                CONSUMER_GROUP, self.consumer_name, {self.stream_key: ">"}, count=1, block=BLOCK_MS
            )
            if not response:
                continue
            for _stream_key, messages in response:
                for message_id, fields in messages:
                    self._process_message(message_id, fields)

    def _process_message(self, message_id: bytes, fields: dict) -> None:
        track_id = fields[b"track_id"].decode()
        captured_at = datetime.fromisoformat(fields[b"captured_at"].decode())
        try:
            frame = decode_jpeg(fields[b"jpeg"])
            boxes = run_person_detection(self.model, frame, min_confidence=self.min_confidence)
            with session_scope() as session:
                for box in boxes:
                    detection_id = new_id("det")
                    path = crop_path(self.frame_store_dir, detection_id)
                    save_crop(frame, box, path)
                    session.add(
                        Detection(
                            id=detection_id,
                            track_id=track_id,
                            captured_at=captured_at,
                            bounding_box=box.as_json(),
                            confidence=box.confidence,
                            frame_path=path,
                        )
                    )
        except Exception:
            logger.exception("camera_id=%s track_id=%s failed to process frame", self.camera_id, track_id)
        finally:
            self.redis_client.xack(self.stream_key, CONSUMER_GROUP, message_id)
