from datetime import datetime, timezone


def _create_camera(client):
    response = client.post(
        "/api/v1/cameras",
        json={"name": "Lobby North", "lat": 12.9716, "lon": 77.5946, "stream_url": "rtsp://camera-host/lobby-north"},
    )
    return response.json()


def _insert_track_with_detection(camera_id: str) -> tuple[str, str]:
    from common.db import session_scope
    from common.ids import new_id
    from common.models import Detection, Track

    track_id = new_id("trk")
    detection_id = new_id("det")
    with session_scope() as session:
        session.add(Track(id=track_id, camera_id=camera_id, started_at=datetime.now(timezone.utc)))
        session.add(
            Detection(
                id=detection_id,
                track_id=track_id,
                captured_at=datetime.now(timezone.utc),
                bounding_box={"x": 1, "y": 2, "w": 3, "h": 4},
                confidence=0.9,
            )
        )
    return track_id, detection_id


def test_camera_tracks_and_track_detections(client):
    camera = _create_camera(client)
    track_id, detection_id = _insert_track_with_detection(camera["id"])

    tracks = client.get(f"/api/v1/cameras/{camera['id']}/tracks").json()
    assert [t["id"] for t in tracks["data"]] == [track_id]

    track = client.get(f"/api/v1/tracks/{track_id}").json()
    assert track["camera_id"] == camera["id"]

    detections = client.get(f"/api/v1/tracks/{track_id}/detections").json()
    assert [d["id"] for d in detections["data"]] == [detection_id]
    assert detections["data"][0]["bounding_box"] == {"x": 1, "y": 2, "w": 3, "h": 4}


def test_get_missing_track_returns_envelope_error(client):
    response = client.get("/api/v1/tracks/trk_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "track_not_found"


def test_delete_camera_with_tracks_is_blocked(client):
    camera = _create_camera(client)
    _insert_track_with_detection(camera["id"])

    response = client.delete(f"/api/v1/cameras/{camera['id']}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "camera_has_tracks"
