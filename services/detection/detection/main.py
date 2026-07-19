"""Detection service entrypoint.

Mirrors ingestion's poll loop: keeps one DetectionWorker running per camera that's
currently streaming, consuming that camera's frame queue via a Redis consumer group
(docs/DECISIONS.md ADR-0005) so a second detection worker could later join the same
group and split the work (Phase 2).
"""

import logging
import os
import time

import redis
from common.db import session_scope
from common.models import Camera
from common.worker_pool import diff_ids
from sqlalchemy import select
from ultralytics import YOLO

from detection.worker import DetectionWorker

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = float(os.environ.get("DETECTION_POLL_INTERVAL_SECONDS", "5"))
MIN_CONFIDENCE = float(os.environ.get("DETECTION_MIN_CONFIDENCE", "0.5"))
FRAME_STORE_DIR = os.environ.get("FRAME_STORE_DIR", "/data/frames")
WORKER_ID = os.environ.get("WORKER_ID", "detection-1")


def get_streaming_camera_ids() -> set[str]:
    with session_scope() as session:
        rows = session.execute(select(Camera.id).where(Camera.status == "streaming")).scalars().all()
        return set(rows)


def run(poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    redis_client = redis.Redis.from_url(os.environ["REDIS_URL"])
    model = YOLO("yolov8n.pt")
    workers: dict[str, DetectionWorker] = {}

    logger.info("detection service starting, worker_id=%s", WORKER_ID)
    while True:
        streaming_ids = get_streaming_camera_ids()
        to_start, to_stop = diff_ids(streaming_ids, set(workers))

        for camera_id in to_stop:
            workers.pop(camera_id).stop()
            logger.info("camera_id=%s detection stopped", camera_id)

        for camera_id in to_start:
            worker = DetectionWorker(
                camera_id=camera_id,
                model=model,
                redis_client=redis_client,
                frame_store_dir=FRAME_STORE_DIR,
                consumer_name=WORKER_ID,
                min_confidence=MIN_CONFIDENCE,
            )
            worker.start()
            workers[camera_id] = worker
            logger.info("camera_id=%s detection started", camera_id)

        time.sleep(poll_interval)


if __name__ == "__main__":
    run()
