from datetime import timedelta

from common.db import session_scope
from common.ids import new_id
from common.models import Camera, Identity, Sighting, Track, utcnow

from retention.gc import run_gc_pass


def test_run_gc_pass_deletes_stale_identity_and_keeps_fresh():
    now = utcnow()
    with session_scope() as session:
        camera = Camera(id=new_id("cam"), name="Lobby", lat=0.0, lon=0.0, stream_url="0")
        session.add(camera)

        stale_track = Track(id=new_id("trk"), camera_id=camera.id, started_at=now - timedelta(days=200))
        session.add(stale_track)
        stale_identity = Identity(id=new_id("idn"), first_seen=now - timedelta(days=200), last_seen=now - timedelta(days=200), embedding=[0.1])
        session.add(stale_identity)
        session.add(
            Sighting(
                id=new_id("sgt"),
                identity_id=stale_identity.id,
                track_id=stale_track.id,
                camera_id=camera.id,
                seen_at=now - timedelta(days=200),
                match_confidence=0.9,
            )
        )

        fresh_track = Track(id=new_id("trk"), camera_id=camera.id, started_at=now)
        session.add(fresh_track)
        fresh_identity = Identity(id=new_id("idn"), first_seen=now, last_seen=now, embedding=[0.1])
        session.add(fresh_identity)
        session.add(
            Sighting(
                id=new_id("sgt"), identity_id=fresh_identity.id, track_id=fresh_track.id, camera_id=camera.id, seen_at=now, match_confidence=0.9
            )
        )
        stale_identity_id, fresh_identity_id = stale_identity.id, fresh_identity.id

    stats = run_gc_pass(retention_days=90)

    assert stats.identities == 1
    with session_scope() as session:
        assert session.get(Identity, stale_identity_id) is None
        assert session.get(Identity, fresh_identity_id) is not None
