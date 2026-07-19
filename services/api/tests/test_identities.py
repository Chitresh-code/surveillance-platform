from datetime import datetime, timezone


def _create_camera(client):
    response = client.post(
        "/api/v1/cameras",
        json={"name": "Lobby North", "lat": 12.9716, "lon": 77.5946, "stream_url": "rtsp://camera-host/lobby-north"},
    )
    return response.json()


def _insert_identity_with_sighting(camera_id: str, embedding=None) -> tuple[str, str, str]:
    from common.db import session_scope
    from common.ids import new_id
    from common.models import Identity, Sighting, Track

    track_id = new_id("trk")
    identity_id = new_id("idn")
    sighting_id = new_id("sgt")
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        session.add(Track(id=track_id, camera_id=camera_id, started_at=now, ended_at=now))
        session.add(Identity(id=identity_id, first_seen=now, last_seen=now, embedding=embedding or [1.0, 0.0]))
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


def test_get_identity_and_list_sightings(client):
    camera = _create_camera(client)
    identity_id, track_id, sighting_id = _insert_identity_with_sighting(camera["id"])

    identity = client.get(f"/api/v1/identities/{identity_id}").json()
    assert identity["id"] == identity_id
    assert "embedding" not in identity

    sightings = client.get(f"/api/v1/identities/{identity_id}/sightings").json()
    assert [s["id"] for s in sightings["data"]] == [sighting_id]
    assert sightings["data"][0]["track_id"] == track_id


def test_get_missing_identity_returns_envelope_error(client):
    response = client.get("/api/v1/identities/idn_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "identity_not_found"


def test_list_identities_paginates(client):
    camera = _create_camera(client)
    for _ in range(3):
        _insert_identity_with_sighting(camera["id"])

    response = client.get("/api/v1/identities", params={"limit": 2})
    body = response.json()
    assert len(body["data"]) == 2
    assert body["next_cursor"] is not None


def test_merge_identity_reassigns_sightings_and_deletes_the_other(client):
    camera = _create_camera(client)
    identity_a, _, sighting_a = _insert_identity_with_sighting(camera["id"])
    identity_b, _, sighting_b = _insert_identity_with_sighting(camera["id"])

    response = client.post(f"/api/v1/identities/{identity_a}/merge", json={"merge_identity_id": identity_b})
    assert response.status_code == 200
    assert response.json()["id"] == identity_a

    sightings = client.get(f"/api/v1/identities/{identity_a}/sightings").json()
    assert {s["id"] for s in sightings["data"]} == {sighting_a, sighting_b}
    assert client.get(f"/api/v1/identities/{identity_b}").status_code == 404


def test_merge_identity_into_itself_is_rejected(client):
    camera = _create_camera(client)
    identity_id, _, _ = _insert_identity_with_sighting(camera["id"])

    response = client.post(f"/api/v1/identities/{identity_id}/merge", json={"merge_identity_id": identity_id})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_merge"


def test_split_identity_detaches_the_track_into_a_new_identity(client):
    camera = _create_camera(client)
    identity_id, track_id, sighting_id = _insert_identity_with_sighting(camera["id"])

    response = client.post(f"/api/v1/identities/{identity_id}/split", json={"track_id": track_id})
    assert response.status_code == 200
    new_identity_id = response.json()["id"]
    assert new_identity_id != identity_id

    sightings = client.get(f"/api/v1/identities/{new_identity_id}/sightings").json()
    assert [s["id"] for s in sightings["data"]] == [sighting_id]


def test_split_with_unrelated_track_returns_envelope_error(client):
    camera = _create_camera(client)
    identity_id, _, _ = _insert_identity_with_sighting(camera["id"])

    response = client.post(f"/api/v1/identities/{identity_id}/split", json={"track_id": "trk_missing"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sighting_not_found"
