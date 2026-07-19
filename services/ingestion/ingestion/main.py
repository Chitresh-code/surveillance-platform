"""Ingestion service entrypoint.

Polls the metadata store for cameras with status="streaming" and keeps one
CameraWorker running per such camera, starting/stopping workers as the API
flips a camera's status (POST /cameras/{id}/stream/start|stop). Frames are
tagged with camera_id only (via the per-camera stream key); associating
frames into per-person tracks is the detection service's job, since that's
where the tracker runs (docs/DECISIONS.md ADR-0007).
"""

import logging
import os
import time

import redis
from common.db import session_scope
from common.models import Camera
from common.worker_pool import diff_ids
from sqlalchemy import select

from ingestion.capture import CameraWorker

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = float(os.environ.get("INGESTION_POLL_INTERVAL_SECONDS", "5"))
TARGET_FPS = float(os.environ.get("INGESTION_TARGET_FPS", "5"))


def get_streaming_cameras() -> dict[str, Camera]:
    with session_scope() as session:
        rows = session.execute(select(Camera).where(Camera.status == "streaming")).scalars().all()
        return {row.id: row for row in rows}


def run(poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    redis_client = redis.Redis.from_url(os.environ["REDIS_URL"])
    workers: dict[str, CameraWorker] = {}

    logger.info("ingestion service starting, polling every %ss", poll_interval)
    while True:
        cameras = get_streaming_cameras()
        to_start, to_stop = diff_ids(set(cameras), set(workers))

        for camera_id in to_stop:
            workers.pop(camera_id).stop()
            logger.info("camera_id=%s ingestion stopped", camera_id)

        for camera_id in to_start:
            camera = cameras[camera_id]
            worker = CameraWorker(
                camera_id=camera_id,
                stream_url=camera.stream_url,
                redis_client=redis_client,
                target_fps=TARGET_FPS,
            )
            worker.start()
            workers[camera_id] = worker
            logger.info("camera_id=%s ingestion started", camera_id)

        time.sleep(poll_interval)


if __name__ == "__main__":
    run()
