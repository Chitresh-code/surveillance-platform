# Surveillance Platform

A multi-camera video surveillance platform. It ingests video from several cameras, detects and tracks people within each camera's view, and re-identifies the same person as they move between cameras. Detections, tracks, and identity matches land in a metadata store, queryable through a REST API, with a map view showing where activity is happening.

## Status

Phase 1 (single camera: ingestion, detection, storage, minimal API) and Phase 2 (multiple cameras, tracking within each) are implemented. Cross-camera re-identification (Phase 3) and the map UI (Phase 4) are next. See the roadmap in [docs/PRD.md](docs/PRD.md) for what's planned and in what order, and [docs/DECISIONS.md](docs/DECISIONS.md) for why each piece of the stack was chosen.

## Services

| Service | Does |
|---|---|
| `services/common` | Shared SQLAlchemy models, DB session helper, Alembic migrations, id/pagination helpers. |
| `services/ingestion` | Reads each streaming camera via OpenCV, publishes frames onto a per-camera Redis stream. |
| `services/detection` | Consumes frames, runs YOLOv8n person detection, tracks people within a camera with ByteTrack, stores detections/tracks and frame crops. |
| `services/api` | FastAPI REST API over the metadata store, per [docs/API_SPEC.md](docs/API_SPEC.md). |

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

This brings up `metadata-db` (Postgres), `frame-queue` (Redis), a one-off `migrate` job that applies Alembic migrations, then `api`, `ingestion`, and `detection`. The API is at `http://localhost:8000/api/v1`.

Register a camera and start streaming it:

```sh
curl -X POST http://localhost:8000/api/v1/cameras \
  -H "Content-Type: application/json" \
  -d '{"name": "Lobby North", "lat": 12.9716, "lon": 77.5946, "stream_url": "rtsp://camera-host/lobby-north"}'

curl -X POST http://localhost:8000/api/v1/cameras/{camera_id}/stream/start
```

Tracks and their detections then land under `GET /api/v1/cameras/{camera_id}/tracks` and `GET /api/v1/tracks/{track_id}/detections`. Full contract in [docs/API_SPEC.md](docs/API_SPEC.md).

### Running tests locally

Each service manages its own dependencies with [`uv`](https://docs.astral.sh/uv/):

```sh
cd services/<service> && uv run pytest
```

## Contributing

See [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) before opening a PR: commit format, branch naming, and review expectations are there.

## License

MIT, see [LICENSE](LICENSE).
