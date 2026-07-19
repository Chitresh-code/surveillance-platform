"""Cascade deletion of identities and their tracks/detections/frame crops
(docs/DECISIONS.md ADR-0011). Shared by the retention/GC service and the
API's manual identity-delete endpoint so there's one deletion path, not two.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from common.models import Detection, Identity, Sighting, Track


@dataclass
class PurgeStats:
    identities: int = field(default=0)
    tracks: int = field(default=0)
    sightings: int = field(default=0)
    detections: int = field(default=0)


def _delete_track(session: Session, track: Track, stats: PurgeStats) -> None:
    for detection in session.query(Detection).filter(Detection.track_id == track.id):
        if detection.frame_path:
            Path(detection.frame_path).unlink(missing_ok=True)
        stats.detections += 1
    session.query(Detection).filter(Detection.track_id == track.id).delete(synchronize_session=False)
    session.delete(track)
    stats.tracks += 1


def delete_identity(session: Session, identity: Identity) -> PurgeStats:
    """Delete an identity and every track/detection/frame that exists only to describe it."""
    stats = PurgeStats(identities=1)
    for sighting in list(identity.sightings):
        track = session.get(Track, sighting.track_id)
        session.delete(sighting)
        stats.sightings += 1
        if track is not None:
            _delete_track(session, track, stats)
    session.delete(identity)
    return stats


def gc_expired(session: Session, cutoff: datetime) -> PurgeStats:
    """Delete identities last seen before `cutoff`, plus tracks that never matched
    an identity (no sighting) and were started before `cutoff`.
    """
    stats = PurgeStats()
    for identity in session.query(Identity).filter(Identity.last_seen < cutoff):
        identity_stats = delete_identity(session, identity)
        stats.identities += identity_stats.identities
        stats.sightings += identity_stats.sightings
        stats.tracks += identity_stats.tracks
        stats.detections += identity_stats.detections

    orphan_tracks = (
        session.query(Track)
        .outerjoin(Sighting, Sighting.track_id == Track.id)
        .filter(Track.started_at < cutoff, Sighting.id.is_(None))
    )
    for track in list(orphan_tracks):
        _delete_track(session, track, stats)

    return stats
