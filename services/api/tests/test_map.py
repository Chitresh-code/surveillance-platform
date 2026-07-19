from datetime import datetime, timezone


def _create_camera(client, name="Lobby North"):
    response = client.post(
        "/api/v1/cameras",
        json={"name": name, "lat": 12.9716, "lon": 77.5946, "stream_url": "rtsp://camera-host/lobby-north"},
    )
    return response.json()


def _insert_identity_with_sighting(camera_id: str) -> tuple[str, str]:
    from common.db import session_scope
    from common.ids import new_id
    from common.models import Identity, Sighting, Track

    track_id = new_id("trk")
    identity_id = new_id("idn")
    sighting_id = new_id("sgt")
    now = datetime.now(timezone.utc)
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
    return identity_id, sighting_id


def test_map_cameras_includes_location_and_status_but_not_stream_url(client):
    camera = _create_camera(client, "Map Cam")

    response = client.get("/api/v1/map/cameras")
    matching = [c for c in response.json()["data"] if c["id"] == camera["id"]]
    assert matching[0]["lat"] == camera["lat"]
    assert matching[0]["status"] == "idle"
    assert "stream_url" not in matching[0]


def test_map_activity_joins_camera_location_and_orders_most_recent_first(client):
    camera = _create_camera(client, "Map Activity Cam")
    identity_id, sighting_id = _insert_identity_with_sighting(camera["id"])

    response = client.get("/api/v1/map/activity")
    body = response.json()
    matching = [a for a in body["data"] if a["id"] == sighting_id]
    assert matching[0]["identity_id"] == identity_id
    assert matching[0]["lat"] == camera["lat"]
    assert matching[0]["lon"] == camera["lon"]
