"""Ingestion service entrypoint.

Polls the metadata store for cameras with status="streaming" and keeps one
CameraWorker running per such camera, starting/stopping workers as the API
flips a camera's status (POST /cameras/{id}/stream/start|stop).
"""

import logging
import os
import time
from datetime import datetime, timezone

import redis
from common.db import session_scope
from common.ids import new_id
from common.models import Camera, Track
from common.worker_pool import diff_camera_sets
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


def open_track(camera_id: str) -> str:
    track_id = new_id("trk")
    with session_scope() as session:
        session.add(Track(id=track_id, camera_id=camera_id, started_at=datetime.now(timezone.utc)))
    return track_id


def close_track(track_id: str) -> None:
    with session_scope() as session:
        track = session.get(Track, track_id)
        if track is not None:
            track.ended_at = datetime.now(timezone.utc)


def run(poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    redis_client = redis.Redis.from_url(os.environ["REDIS_URL"])
    workers: dict[str, CameraWorker] = {}

    logger.info("ingestion service starting, polling every %ss", poll_interval)
    while True:
        cameras = get_streaming_cameras()
        to_start, to_stop = diff_camera_sets(set(cameras), set(workers))

        for camera_id in to_stop:
            worker = workers.pop(camera_id)
            worker.stop()
            close_track(worker.track_id)
            logger.info("camera_id=%s track_id=%s ingestion stopped", camera_id, worker.track_id)

        for camera_id in to_start:
            camera = cameras[camera_id]
            track_id = open_track(camera_id)
            worker = CameraWorker(
                camera_id=camera_id,
                stream_url=camera.stream_url,
                track_id=track_id,
                redis_client=redis_client,
                target_fps=TARGET_FPS,
            )
            worker.start()
            workers[camera_id] = worker
            logger.info("camera_id=%s track_id=%s ingestion started", camera_id, track_id)

        time.sleep(poll_interval)


if __name__ == "__main__":
    run()
