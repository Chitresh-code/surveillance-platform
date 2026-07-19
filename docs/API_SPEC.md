# API Specification

This is the contract for the REST API described in docs/ARCHITECTURE.md. It's written ahead of implementation, so treat it as the target, not a description of existing code. Once endpoints are built, a Postman collection under `postman/` will mirror this document — if the two drift, this document wins and the collection gets fixed.

## 1. Conventions

- Base path: `/api/v1`.
- Request and response bodies are JSON.
- Timestamps are ISO 8601 UTC (`2026-07-19T14:02:31Z`).
- IDs are opaque strings (not assumed to be sequential integers).
- List endpoints are paginated with `limit` (default 50, max 200) and `cursor` query params; responses include a `next_cursor` (`null` when there's no more data).
- Filtering on list endpoints uses query params named after the field (`camera_id`, `identity_id`, `from`, `to`).
- Errors use a consistent envelope (see §5) and standard HTTP status codes.
- Auth mechanism is not yet decided — see docs/DECISIONS.md. Until it lands, assume every endpoint requires a bearer token and treat the API as running behind a private network boundary in development.

## 2. Resources

| Resource | Represents |
|---|---|
| `Camera` | A registered video source and its map location. |
| `Track` | One continuous observation of a subject on one camera. |
| `Detection` | A single frame's bounding box within a track. |
| `Identity` | A cross-camera cluster of tracks believed to be the same subject. |
| `Sighting` | A link between a track and an identity, with a match confidence. |
| `Event` | A queryable, denormalized view over sightings for the API's read side. |

## 3. Endpoints

### Cameras

| Method | Path | Purpose |
|---|---|---|
| GET | `/cameras` | List registered cameras. |
| POST | `/cameras` | Register a new camera. |
| GET | `/cameras/{camera_id}` | Get one camera. |
| PATCH | `/cameras/{camera_id}` | Update name/location/config. |
| DELETE | `/cameras/{camera_id}` | Remove a camera and stop its ingestion. |
| POST | `/cameras/{camera_id}/stream/start` | Start ingesting this camera's stream. |
| POST | `/cameras/{camera_id}/stream/stop` | Stop ingesting this camera's stream. |

### Tracks & detections

| Method | Path | Purpose |
|---|---|---|
| GET | `/cameras/{camera_id}/tracks` | List tracks for a camera, filterable by time range. |
| GET | `/tracks/{track_id}` | Get one track. |
| GET | `/tracks/{track_id}/detections` | List per-frame detections within a track. |

### Identities

| Method | Path | Purpose |
|---|---|---|
| GET | `/identities` | List known identities. |
| GET | `/identities/{identity_id}` | Get one identity. |
| GET | `/identities/{identity_id}/sightings` | List sightings for an identity across all cameras. |
| POST | `/identities/{identity_id}/merge` | Merge another identity into this one (operator correction). |
| POST | `/identities/{identity_id}/split` | Detach a track into a new identity (operator correction). |

### Events

| Method | Path | Purpose |
|---|---|---|
| GET | `/events` | List events, filterable by `camera_id`, `identity_id`, `from`, `to`. |
| GET | `/events/{event_id}` | Get one event. |

### Map

| Method | Path | Purpose |
|---|---|---|
| GET | `/map/cameras` | Camera locations plus current ingestion status, for map markers. |
| GET | `/map/activity` | Recent sightings suitable for a map overlay (identity, camera, location, time). |

## 4. Example payloads

**`POST /cameras`**

```json
{
  "name": "Lobby North",
  "lat": 12.9716,
  "lon": 77.5946,
  "stream_url": "rtsp://camera-host/lobby-north"
}
```

**`GET /identities/{identity_id}/sightings`**

```json
{
  "data": [
    {
      "id": "sgt_8f2c",
      "identity_id": "idn_4a11",
      "track_id": "trk_991b",
      "camera_id": "cam_lobby_north",
      "seen_at": "2026-07-19T14:02:31Z",
      "match_confidence": 0.87
    }
  ],
  "next_cursor": null
}
```

**`POST /identities/{identity_id}/merge`**

```json
{
  "merge_identity_id": "idn_7b02"
}
```

## 5. Error format

```json
{
  "error": {
    "code": "camera_not_found",
    "message": "No camera with id cam_9f21."
  }
}
```

`code` is a stable machine-readable string; `message` is for humans and may change wording without notice. HTTP status carries the category (404, 400, 409, 500, etc.) — clients should branch on `code`, not on `message`.

## 6. Versioning

Breaking changes get a new base path (`/api/v2`); additive changes (new optional fields, new endpoints) land in `/api/v1` without a bump.

## 7. Open items

- Auth scheme (docs/DECISIONS.md).
- Whether `Event` is a real stored table or a view computed from `Sighting` — implementation detail, doesn't change this contract either way.
- Rate limiting policy for integrator API keys.
