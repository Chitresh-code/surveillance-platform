"""Re-identification service entrypoint. Runs a single ReidWorker consuming the shared
`tracks:ready` stream (docs/ARCHITECTURE.md: re-id triggers when a track closes).
"""

import logging
import os

import redis

from reid.embedder import build_encoder
from reid.worker import ReidWorker

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

MATCH_THRESHOLD = float(os.environ.get("REID_MATCH_THRESHOLD", "0.6"))
WORKER_ID = os.environ.get("WORKER_ID", "reid-1")


def run() -> None:
    redis_client = redis.Redis.from_url(os.environ["REDIS_URL"])
    encoder = build_encoder()
    worker = ReidWorker(
        encoder=encoder, redis_client=redis_client, consumer_name=WORKER_ID, match_threshold=MATCH_THRESHOLD
    )
    logger.info("reid service starting, worker_id=%s", WORKER_ID)
    worker.run_forever()


if __name__ == "__main__":
    run()
