def _create_camera(client, name="Lobby North"):
    response = client.post(
        "/api/v1/cameras",
        json={"name": name, "lat": 12.9716, "lon": 77.5946, "stream_url": "rtsp://camera-host/lobby-north"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_get_camera(client):
    camera = _create_camera(client)
    assert camera["status"] == "idle"

    response = client.get(f"/api/v1/cameras/{camera['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Lobby North"


def test_get_missing_camera_returns_envelope_error(client):
    response = client.get("/api/v1/cameras/cam_does_not_exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "camera_not_found"


def test_list_cameras_paginates(client):
    for i in range(3):
        _create_camera(client, name=f"Cam {i}")

    response = client.get("/api/v1/cameras", params={"limit": 2})
    body = response.json()
    assert len(body["data"]) == 2
    assert body["next_cursor"] is not None

    response2 = client.get("/api/v1/cameras", params={"limit": 2, "cursor": body["next_cursor"]})
    assert response2.status_code == 200


def test_update_camera(client):
    camera = _create_camera(client)
    response = client.patch(f"/api/v1/cameras/{camera['id']}", json={"name": "Lobby South"})
    assert response.status_code == 200
    assert response.json()["name"] == "Lobby South"


def test_stream_start_and_stop(client):
    camera = _create_camera(client)

    started = client.post(f"/api/v1/cameras/{camera['id']}/stream/start")
    assert started.json()["status"] == "streaming"

    stopped = client.post(f"/api/v1/cameras/{camera['id']}/stream/stop")
    assert stopped.json()["status"] == "idle"


def test_delete_camera(client):
    camera = _create_camera(client)
    response = client.delete(f"/api/v1/cameras/{camera['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/v1/cameras/{camera['id']}").status_code == 404
