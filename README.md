# Surveillance Platform

A multi-camera video surveillance platform. It ingests video from several cameras, detects and tracks people within each camera's view, and re-identifies the same person as they move between cameras. Detections, tracks, and identity matches land in a metadata store, queryable through a REST API, with a map view showing where activity is happening.

## Status

Early / docs-first. There's no service code yet — this repo currently holds the product spec, architecture, and API contract that implementation will follow. See the roadmap in [docs/PRD.md](docs/PRD.md) for what's planned and in what order.

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

Nothing to run yet. Once the first service lands, this section covers local setup and `docker compose up`.

## Contributing

See [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) before opening a PR — commit format, branch naming, and review expectations are there.

## License

MIT — see [LICENSE](LICENSE).
