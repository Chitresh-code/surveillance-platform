from datetime import datetime, timezone


def _create_camera(client, name="Lobby North"):
    response = client.post(
        "/api/v1/cameras",
        json={"name": name, "lat": 12.9716, "lon": 77.5946, "stream_url": "rtsp://camera-host/lobby-north"},
    )
    return response.json()


def _insert_identity_with_sighting(camera_id: str, seen_at: datetime | None = None) -> tuple[str, str, str]:
    from common.db import session_scope
    from common.ids import new_id
    from common.models import Identity, Sighting, Track

    track_id = new_id("trk")
    identity_id = new_id("idn")
    sighting_id = new_id("sgt")
    now = seen_at or datetime.now(timezone.utc)
    with session_scope() as session:
        session.add(Track(id=track_id, camera_id=camera_id, started_at=now, ended_at=now))
        session.add(Identity(id=identity_id, first_seen=now, last_seen=now, embedding=[1.0, 0.0]))
        session.add(
            Sighting(
                id=sighting_id,
                identity_id=identity_id,
                track_id=track_id,
                camera_id=camera_id,
                seen_at=now,
                match_confidence=0.87,
            )
        )
    return identity_id, track_id, sighting_id


def test_get_event(client):
    camera = _create_camera(client)
    identity_id, track_id, sighting_id = _insert_identity_with_sighting(camera["id"])

    response = client.get(f"/api/v1/events/{sighting_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["identity_id"] == identity_id
    assert body["track_id"] == track_id


def test_get_missing_event_returns_envelope_error(client):
    response = client.get("/api/v1/events/sgt_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "event_not_found"


def test_list_events_filters_by_camera_and_identity(client):
    camera_a = _create_camera(client, "Camera A")
    camera_b = _create_camera(client, "Camera B")
    identity_a, _, sighting_a = _insert_identity_with_sighting(camera_a["id"])
    identity_b, _, sighting_b = _insert_identity_with_sighting(camera_b["id"])

    by_camera = client.get("/api/v1/events", params={"camera_id": camera_a["id"]}).json()
    assert [e["id"] for e in by_camera["data"]] == [sighting_a]

    by_identity = client.get("/api/v1/events", params={"identity_id": identity_b}).json()
    assert [e["id"] for e in by_identity["data"]] == [sighting_b]


def test_list_events_filters_by_time_range(client):
    camera = _create_camera(client, "Camera C")
    old = datetime(2020, 1, 1, tzinfo=timezone.utc)
    _, _, old_sighting = _insert_identity_with_sighting(camera["id"], seen_at=old)
    _, _, recent_sighting = _insert_identity_with_sighting(camera["id"])

    response = client.get("/api/v1/events", params={"camera_id": camera["id"], "from": "2025-01-01T00:00:00Z"})
    ids = [e["id"] for e in response.json()["data"]]
    assert ids == [recent_sighting]
    assert old_sighting not in ids
