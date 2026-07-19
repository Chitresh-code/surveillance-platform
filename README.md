# Surveillance Platform

A multi-camera video surveillance platform. It ingests video from several cameras, detects and tracks people within each camera's view, and re-identifies the same person as they move between cameras. Detections, tracks, and identity matches land in a metadata store, queryable through a REST API, with a map view showing where activity is happening.

## Status

Phase 1 (single camera: ingestion, detection, storage, minimal API), Phase 2 (multiple cameras, tracking within each), Phase 3 (cross-camera re-identification), and Phase 4 (map UI, full API surface, Postman collection, Docker deployment polish) are implemented. See the roadmap in [docs/PRD.md](docs/PRD.md) for what's planned and in what order, and [docs/DECISIONS.md](docs/DECISIONS.md) for why each piece of the stack was chosen.

## Services

| Service | Does |
|---|---|
| `services/common` | Shared SQLAlchemy models, DB session helper, Alembic migrations, id/pagination helpers. |
| `services/ingestion` | Reads each streaming camera via OpenCV, publishes frames onto a per-camera Redis stream. |
| `services/detection` | Consumes frames, runs YOLOv8n person detection, tracks people within a camera with ByteTrack, stores detections/tracks and frame crops, publishes closed tracks for re-identification. |
| `services/reid` | Consumes closed tracks, computes an appearance embedding for each, and matches or creates identities/sightings. |
| `services/api` | FastAPI REST API over the metadata store, per [docs/API_SPEC.md](docs/API_SPEC.md). |
| `frontend` | React + Leaflet map UI: camera markers and recent-sighting overlay, a client of the REST API only. |

## Documentation

| Doc | Covers |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Problem, requirements, roadmap |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data flow, deployment topology |
| [docs/API_SPEC.md](docs/API_SPEC.md) | REST endpoints and payloads |
| [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Repo layout, commit/PR conventions |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture decision log |
| [docs/TESTING.md](docs/TESTING.md) | Test strategy by layer |

## Getting started

Requires Docker and Docker Compose. `.env.example` documents the Postgres credentials; the defaults work as-is for local use, so copying it to `.env` is optional.

```sh
docker compose up --build
```

This brings up `metadata-db` (Postgres), `frame-queue` (Redis), a one-off `migrate` job that applies Alembic migrations, then `api`, `ingestion`, `detection`, `reid`, and `frontend`. The API is at `http://localhost:8000/api/v1`, the map UI at `http://localhost:5173`.

Register a camera and start streaming it:

```sh
curl -X POST http://localhost:8000/api/v1/cameras \
  -H "Content-Type: application/json" \
  -d '{"name": "Lobby North", "lat": 12.9716, "lon": 77.5946, "stream_url": "rtsp://camera-host/lobby-north"}'

curl -X POST http://localhost:8000/api/v1/cameras/{camera_id}/stream/start
```

Tracks and their detections then land under `GET /api/v1/cameras/{camera_id}/tracks` and `GET /api/v1/tracks/{track_id}/detections`. Once a track closes, `reid` matches it against known identities:

```sh
curl http://localhost:8000/api/v1/identities
curl http://localhost:8000/api/v1/identities/{identity_id}/sightings
```

Operators can correct a matching mistake with `POST /api/v1/identities/{identity_id}/merge` (fold another identity into this one) or `POST /api/v1/identities/{identity_id}/split` (detach a track into a new identity). Full contract in [docs/API_SPEC.md](docs/API_SPEC.md).

`GET /api/v1/events` gives the same sightings as a filterable, cross-camera feed (`camera_id`, `identity_id`, `from`, `to` query params); `GET /api/v1/map/cameras` and `GET /api/v1/map/activity` are what the map UI polls for markers and the recent-activity overlay:

```sh
curl "http://localhost:8000/api/v1/events?camera_id={camera_id}"
curl http://localhost:8000/api/v1/map/cameras
curl http://localhost:8000/api/v1/map/activity
```

### Map UI

`docker compose up --build` builds and serves `frontend/` at `http://localhost:5173` (nginx serving the Vite production build, API base URL baked in at build time via the `VITE_API_BASE_URL` build arg). For local dev with hot reload instead:

```sh
cd frontend
npm install
cp .env.example .env.local   # VITE_API_BASE_URL, defaults to http://localhost:8000/api/v1
npm run dev
```

### API collection

[`postman/surveillance-platform.postman_collection.json`](postman/surveillance-platform.postman_collection.json) mirrors [docs/API_SPEC.md](docs/API_SPEC.md); import it into Postman and set the `base_url` collection variable if not running on the default port.

### Running tests locally

Each service manages its own dependencies with [`uv`](https://docs.astral.sh/uv/):

```sh
cd services/<service> && uv run pytest
```

## Contributing

See [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) before opening a PR: commit format, branch naming, and review expectations are there.

## License

MIT, see [LICENSE](LICENSE).
