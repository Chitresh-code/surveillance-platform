"""Per-camera capture worker (docs/ARCHITECTURE.md: Ingestion Service).

Reads frames from a camera's stream_url (docs/DECISIONS.md ADR-0003: cv2.VideoCapture)
and pushes JPEG-encoded frames onto a Redis stream (ADR-0005) for the detection
service to consume. A dropped connection is retried here so it never takes down
another camera's ingestion (docs/ARCHITECTURE.md §1). Frames carry no track_id:
associating them into per-person tracks happens in the detection service, which
is where the tracker runs (ADR-0007).
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import cv2
import redis

logger = logging.getLogger(__name__)

RECONNECT_BACKOFF_SECONDS = 2
MAX_RECONNECT_BACKOFF_SECONDS = 30


def frame_stream_key(camera_id: str) -> str:
    return f"frames:{camera_id}"


def build_frame_fields(frame) -> dict[str, bytes | str]:
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise ValueError("failed to JPEG-encode frame")
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "jpeg": buf.tobytes(),
    }


@dataclass
class CameraWorker:
    camera_id: str
    stream_url: str
    redis_client: redis.Redis
    target_fps: float = 5.0

    def __post_init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=10)

    def _run(self) -> None:
        backoff = RECONNECT_BACKOFF_SECONDS
        min_frame_interval = 1.0 / self.target_fps
        while not self._stop_event.is_set():
            capture = cv2.VideoCapture(self.stream_url)
            if not capture.isOpened():
                logger.warning("camera_id=%s could not open stream, retrying in %ss", self.camera_id, backoff)
                capture.release()
                self._stop_event.wait(backoff)
                backoff = min(backoff * 2, MAX_RECONNECT_BACKOFF_SECONDS)
                continue
            backoff = RECONNECT_BACKOFF_SECONDS

            while not self._stop_event.is_set():
                loop_start = time.monotonic()
                ok, frame = capture.read()
                if not ok:
                    logger.warning("camera_id=%s dropped stream, reconnecting", self.camera_id)
                    break
                try:
                    fields = build_frame_fields(frame)
                    self.redis_client.xadd(frame_stream_key(self.camera_id), fields, maxlen=1000, approximate=True)
                except Exception:
                    logger.exception("camera_id=%s failed to publish frame", self.camera_id)
                elapsed = time.monotonic() - loop_start
                self._stop_event.wait(max(0.0, min_frame_interval - elapsed))

            capture.release()
