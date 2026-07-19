"""One GC pass: delete identities/tracks past the retention window (docs/DECISIONS.md ADR-0011)."""

import logging
from datetime import timedelta

from common.db import session_scope
from common.models import utcnow
from common.retention import PurgeStats, gc_expired

logger = logging.getLogger(__name__)


def run_gc_pass(retention_days: int) -> PurgeStats:
    cutoff = utcnow() - timedelta(days=retention_days)
    with session_scope() as session:
        stats = gc_expired(session, cutoff)
    logger.info(
        "gc pass complete identities=%s tracks=%s sightings=%s detections=%s",
        stats.identities,
        stats.tracks,
        stats.sightings,
        stats.detections,
    )
    return stats
