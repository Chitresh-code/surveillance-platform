# API Specification

This is the contract for the REST API described in docs/ARCHITECTURE.md. It's written ahead of implementation, so treat it as the target, not a description of existing code. Once endpoints are built, a Bruno collection under `bruno/` will mirror this document — if the two drift, this document wins and the collection gets fixed.

## 1. Conventions

- Base path: `/api/v1`.
- Request and response bodies are JSON.
- Timestamps are ISO 8601 UTC (`2026-07-19T14:02:31Z`).
- IDs are opaque strings (not assumed to be sequential integers).
- List endpoints are paginated with `limit` (default 50, max 200) and `cursor` query params; responses include a `next_cursor` (`null` when there's no more data).
- Filtering on list endpoints uses query params named after the field (`camera_id`, `identity_id`, `from`, `to`).
- Errors use a consistent envelope (see §5) and standard HTTP status codes.
- Every endpoint except `POST /auth/login`, `GET /health`, and `GET /events/stream` requires `Authorization: Bearer <token>` (docs/DECISIONS.md ADR-0010). A missing or invalid token gets a 401 with `error.code` of `unauthorized`. `GET /health` also sits outside the `/api/v1` base path (it isn't a versioned resource) — it's just `GET /health`. `GET /events/stream` still requires a valid token, but as a `token` query param instead of a header (docs/DECISIONS.md ADR-0012).

## 2. Resources

| Resource | Represents |
|---|---|
| `Camera` | A registered video source and its map location. |
| `Track` | One continuous observation of a subject on one camera. |
| `Detection` | A single frame's bounding box within a track. |
| `Identity` | A cross-camera cluster of tracks believed to be the same subject. |
| `Sighting` | A link between a track and an identity, with a match confidence. |
| `Event` | A queryable, denormalized view over sightings for the API's read side. |
| `AuditLog` | A record of an operator action against an identity (docs/GAPS.md item 7). |

## 3. Endpoints

### Auth

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | Exchange an operator's username/password for a bearer token (12h expiry). The only endpoint that doesn't itself require one. |

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
| DELETE | `/identities/{identity_id}` | Delete an identity and its tracks/detections/frame crops (docs/DECISIONS.md ADR-0011). |
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

### Health

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness/readiness check: a DB round-trip. Unauthenticated, outside `/api/v1`. |

### Audit log

| Method | Path | Purpose |
|---|---|---|
| GET | `/audit-log` | List operator actions, filterable by `operator_id`, `resource_type`, `resource_id` (docs/GAPS.md item 7). |

### Real-time feed

| Method | Path | Purpose |
|---|---|---|
| GET | `/events/stream` | Server-Sent Events stream of newly-created sightings, one JSON object per `data:` line (docs/DECISIONS.md ADR-0012). Auth is a `token` query param, not the `Authorization` header, since `EventSource` can't set custom headers. Best-effort: a client that isn't connected when a sighting happens simply misses it, this isn't a durable/replayable feed — use `GET /events` for the queryable record. |

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

**`POST /auth/login`**

```json
{
  "username": "operator1",
  "password": "correct-horse-battery-staple"
}
```

Response:

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
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

- Whether `Event` is a real stored table or a view computed from `Sighting` — implementation detail, doesn't change this contract either way.
- Rate limiting on `/auth/login` and on API usage generally — not built yet (docs/DECISIONS.md ADR-0010's consequences).
- Operator account management (create/list/deactivate operators via the API instead of the `create_operator` CLI script) — docs/GAPS.md item 2's remaining piece; no dashboard screen for it either.
