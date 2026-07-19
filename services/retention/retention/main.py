"""Retention/GC service entrypoint. Runs a GC pass on a fixed interval, deleting
identities/tracks/detections/frame crops past RETENTION_DAYS (docs/DECISIONS.md ADR-0011).
"""

import logging
import os
import time

from retention.gc import run_gc_pass

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "90"))
GC_INTERVAL_SECONDS = int(os.environ.get("RETENTION_GC_INTERVAL_SECONDS", str(24 * 60 * 60)))


def run_forever() -> None:
    logger.info("retention service starting, retention_days=%s interval_s=%s", RETENTION_DAYS, GC_INTERVAL_SECONDS)
    while True:
        try:
            run_gc_pass(RETENTION_DAYS)
        except Exception:
            logger.exception("gc pass failed")
        time.sleep(GC_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()
