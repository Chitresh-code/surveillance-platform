"""Re-identification worker: consumes closed tracks and matches or creates identities
(docs/ARCHITECTURE.md, docs/DECISIONS.md ADR-0008).

Unlike ingestion/detection, this isn't a per-camera pool: identities are cross-camera,
so one consumer group on the shared `tracks:ready` stream is enough. A bad track must
not take down the worker (docs/CODING_STANDARDS.md §5).
"""

import logging

import cv2
import redis
from common.db import session_scope
from common.ids import new_id
from common.models import Detection, Identity, Sighting, Track
from sqlalchemy import select

from reid.embedder import embed_crop
from reid.matcher import best_match, update_identity_embedding

logger = logging.getLogger(__name__)

TRACKS_READY_STREAM = "tracks:ready"
CONSUMER_GROUP = "reid-workers"
BLOCK_MS = 2000


class ReidWorker:
    def __init__(self, encoder, redis_client: redis.Redis, consumer_name: str, match_threshold: float = 0.6) -> None:
        self.encoder = encoder
        self.redis_client = redis_client
        self.consumer_name = consumer_name
        self.match_threshold = match_threshold

    def run_forever(self) -> None:
        try:
            self.redis_client.xgroup_create(TRACKS_READY_STREAM, CONSUMER_GROUP, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

        while True:
            response = self.redis_client.xreadgroup(
                CONSUMER_GROUP, self.consumer_name, {TRACKS_READY_STREAM: ">"}, count=1, block=BLOCK_MS
            )
            if not response:
                continue
            for _stream_key, messages in response:
                for message_id, fields in messages:
                    self._process_message(message_id, fields)

    def _process_message(self, message_id: bytes, fields: dict) -> None:
        track_id = fields[b"track_id"].decode()
        try:
            with session_scope() as session:
                track = session.get(Track, track_id)
                if track is None:
                    return

                # ponytail: embeds only the highest-confidence crop rather than averaging
                # across the track. Revisit with multi-crop averaging (or smooth_feature
                # over several samples) if single-crop matching proves too noisy.
                detections = session.execute(select(Detection).where(Detection.track_id == track_id)).scalars().all()
                crops = [d for d in detections if d.frame_path]
                if not crops:
                    return
                best_detection = max(crops, key=lambda d: d.confidence)

                image = cv2.imread(best_detection.frame_path)
                if image is None:
                    logger.warning("track_id=%s crop missing on disk, skipping match", track_id)
                    return

                embedding = embed_crop(self.encoder, image)
                if embedding is None:
                    return

                identities = session.execute(select(Identity)).scalars().all()
                identity, score = best_match(embedding, identities)
                seen_at = track.ended_at or track.started_at

                if identity is not None and score >= self.match_threshold:
                    update_identity_embedding(identity, embedding)
                    identity.last_seen = seen_at
                    match_confidence = score
                else:
                    identity = Identity(
                        id=new_id("idn"), first_seen=seen_at, last_seen=seen_at, embedding=embedding.tolist()
                    )
                    session.add(identity)
                    session.flush()
                    match_confidence = 1.0

                session.add(
                    Sighting(
                        id=new_id("sgt"),
                        identity_id=identity.id,
                        track_id=track.id,
                        camera_id=track.camera_id,
                        seen_at=seen_at,
                        match_confidence=match_confidence,
                    )
                )
        except Exception:
            logger.exception("track_id=%s failed to match identity", track_id)
        finally:
            self.redis_client.xack(TRACKS_READY_STREAM, CONSUMER_GROUP, message_id)
