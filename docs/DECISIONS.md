# Architecture Decision Records

One entry per decision. Once an ADR is Accepted, don't edit it to reflect a later change of mind: add a new ADR that supersedes it and link back. History is the point.

Format: **Status**, **Context**, **Decision**, **Consequences**.

## ADR-0001: Backend language and API framework: Python 3.12 + FastAPI

**Status**: Accepted

**Context**: Every Phase 1 component depends on the computer-vision/ML ecosystem, including frame decoding, person detection, and eventually re-id embeddings. The REST API also needs to track docs/API_SPEC.md closely while the contract is still moving.

**Decision**: Python 3.12 for all services. FastAPI for the REST API.

**Consequences**: Python has the deepest, most current library support for video decoding (OpenCV) and detection/embedding models (PyTorch-based); any other language means writing bindings or trailing the CV ecosystem. FastAPI derives its OpenAPI schema from the same Pydantic models used for request/response validation, which keeps docs/API_SPEC.md and the implementation from drifting apart, and its async support matters once the API is serving concurrent reads from the Map UI and integrators. All services sharing a language means common code (DB models, config loading) can move into a shared package once at least two services need it, per docs/CODING_STANDARDS.md §1. CPU-bound detection work needs process-level separation, not threads, to avoid the GIL; that's already the plan via separate detection-worker containers (docs/ARCHITECTURE.md §4).

## ADR-0002: Metadata store: PostgreSQL, via SQLAlchemy + Alembic

**Status**: Accepted

**Context**: The Metadata Store holds cameras, tracks, detections, and (from Phase 3) identities and sightings, per the ERD in docs/ARCHITECTURE.md §3. From Phase 2 onward, multiple detection workers write to it concurrently.

**Decision**: PostgreSQL, accessed through SQLAlchemy, with Alembic managing schema migrations.

**Consequences**: The schema is genuinely relational: tracks belong to cameras, detections belong to tracks, sightings link tracks to identities, so a relational engine fits better than a document store. Postgres handles concurrent writes from multiple workers safely, which SQLite doesn't do well and Phase 2 needs immediately; choosing Postgres now avoids a storage-engine migration one phase later. SQLAlchemy + Alembic is the standard combination for evolving a Python service's schema, and this schema is certain to grow every phase (identities/sightings land in Phase 3). Adds a `metadata-db` container to docker-compose. Every service touching the DB takes a Postgres dependency; local dev needs the DB container running.

## ADR-0003: Video ingestion and frame decoding: OpenCV `VideoCapture`

**Status**: Accepted

**Context**: The Ingestion Service needs to read frames from a camera stream (RTSP) or a recorded file through one interface, per FR-2.

**Decision**: `cv2.VideoCapture` (OpenCV) for reading both RTSP streams and video files.

**Consequences**: OpenCV is already a hard dependency downstream, since detection needs frames as arrays and saving frame crops needs the same encode/decode calls, so using its capture API too avoids adding a second video library for the same job. It handles RTSP and file input through the same interface, avoiding a format-specific branch for FR-2's start/stop behavior. Reconnect/retry logic on a dropped stream (docs/ARCHITECTURE.md §1: "a dropped camera connection is retried here") has to be handled explicitly in application code, since OpenCV doesn't retry on its own. If frame-accurate timestamps or hardware decoding become a bottleneck, this ADR gets revisited with PyAV/GStreamer as the alternative.

## ADR-0004: Person detection model: Ultralytics YOLOv8n

**Status**: Accepted

**Context**: The Detection service needs to find people in each frame (FR-3). Phase 1 scope is detection only: associating detections into tracks across frames is Phase 2 per the PRD roadmap (docs/PRD.md §10), so this ADR covers the detector, not a tracker.

**Decision**: YOLOv8n (`ultralytics` package), using pretrained COCO weights filtered to the `person` class.

**Consequences**: Ships a pretrained person detector out of the box, so Phase 1 needs no training pipeline or labeled data. The nano variant trades accuracy for speed, which matters because Phase 1 is expected to run on CPU-only dev/deploy targets, not a GPU box. It's a maintained model with a stable Python API, keeping detection-worker code to loading the model and running inference rather than hand-written inference plumbing. Accuracy is bounded by a general-purpose pretrained model; there's no domain-specific fine-tuning in Phase 1. If detection precision/recall (docs/PRD.md §9) isn't good enough on real footage, the fix is a larger YOLOv8 variant or fine-tuning, not a different framework, since the `ultralytics` API stays the same either way.

## ADR-0005: Inter-service frame queue: Redis Streams

**Status**: Accepted

**Context**: docs/ARCHITECTURE.md's Frame Queue decouples Ingestion from Detection so a slow detection worker doesn't stall camera reads (§4). Phase 1 is a single camera, but Ingestion and Detection are already separate containers per the architecture, and Phase 2 needs the same queue to fan frames out to multiple detection workers.

**Decision**: Redis Streams as the frame queue.

**Consequences**: Redis is one low-operational-overhead dependency that covers this queue now and is a natural fit for other short-lived, high-churn data later (e.g., caching re-id comparisons in Phase 3), so it isn't single-purpose infrastructure. Streams' consumer groups are what let multiple detection workers split a camera's frames in Phase 2 without extra application code. A heavier broker (Kafka) is more operational weight than a 1-3 camera deployment justifies. Frame payloads should stay small; this is single-camera scale, so JPEG-encoded frame bytes directly in the stream is acceptable for now, but this doesn't scale indefinitely. If throughput requirements outgrow Redis, this ADR gets superseded, not silently swapped.

## ADR-0006: Object/frame store: local filesystem volume (Phase 1 only)

**Status**: Accepted

**Context**: Detection writes representative frame crops to what docs/ARCHITECTURE.md §1 calls the Object/Frame Store. Phase 1 is a single camera, presumably on a single host.

**Decision**: A local Docker volume (plain filesystem) for Phase 1. Revisit with an S3-compatible object store once a second host or horizontally-scaled detection workers need shared access to the same store.

**Consequences**: At single-camera, single-host scale, a networked object store adds a dependency (MinIO/S3 credentials, bucket lifecycle config) nothing yet needs; nothing requires two processes on two hosts to see the same frame crop. This is explicitly a Phase 1-only decision: the moment detection-worker containers scale across hosts (Phase 2/3, per docs/ARCHITECTURE.md §4's `detection-worker x N`), local disk stops working and this ADR gets superseded by an object-store ADR, flagged now so it isn't a surprise later.

## ADR-0007: Within-camera tracking: Ultralytics BYTETracker

**Status**: Accepted

**Context**: Phase 2 (docs/PRD.md §10) adds FR-3's tracking half: associating per-frame person detections into continuous per-subject tracks within one camera, instead of Phase 1's placeholder of one Track row per streaming session. The detection service already loads `ultralytics` for the detector (ADR-0004) and already runs on CPU-only targets.

**Decision**: `ultralytics.trackers.BYTETracker`, driven directly (not through the `model.track()` video-source API, which assumes it owns the capture loop) by calling `tracker.update(results.boxes, frame)` once per frame inside the detection worker, with one tracker instance per camera for that worker's lifetime.

**Consequences**: `ultralytics` already ships BYTETracker and its config (`bytetrack.yaml`), so this adds no tracking-specific dependency beyond `lap`, the linear-assignment solver BYTETracker's own matching step needs, itself a small package with no further pulled-in weight. ByteTrack is IoU/Kalman-filter based, not an embedding model, so it stays CPU-fast and doesn't conflict with the Phase 1 CPU-only constraint. Calling `update()` directly, per frame, fits the existing architecture where the detection worker (not `ultralytics`) owns the frame loop, reading from Redis rather than a video source. Tracker-assigned ids are integers scoped to one in-process tracker instance, not the persistent `trk_` ids the API returns, so the detection worker maps local id to database Track id itself and that mapping does not survive a worker restart: a track still open when the worker restarts is not resumed, it is orphaned open in the database. Track-loss handling here also closes a Track the moment the tracker's per-frame output drops it, rather than waiting out ByteTrack's own lost-track buffer, so a briefly-occluded subject can show up as two Track rows instead of one; both are noted as known simplifications to revisit if track fragmentation turns out to matter in practice. If accuracy on real footage needs appearance matching (not just motion/IoU), this ADR gets revisited with BoT-SORT, which `ultralytics` also ships.

## ADR-0008: Re-identification embedding: Ultralytics ReID encoder (yolo26n-reid.onnx)

**Status**: Accepted

**Context**: Phase 3 (docs/PRD.md §10) adds FR-4/FR-5: generate an appearance embedding for each closed track and match it against known identities across cameras, creating a new identity when nothing clears the confidence threshold. The reid service is new (docs/CODING_STANDARDS.md §1 already reserves `services/reid/`), and per ADR-0001's context this is exactly the "eventually re-id embeddings" work the Python/CV stack was chosen for. It must stay CPU-friendly, consistent with ADR-0004 and ADR-0007.

**Decision**: Reuse `ultralytics.trackers.utils.reid.ReID`, the appearance encoder Ultralytics already ships for BoT-SORT/Deep OC-SORT, loaded with its bundled `yolo26n-reid.onnx` asset (nano variant, auto-downloaded on first use via `attempt_download_asset`, run through `AutoBackend`/`onnxruntime`). The reid worker feeds it a track's single highest-confidence detection crop (already saved to the frame store by detection, ADR-0006) rather than the full frame, since the crop is already a tight person box. Matching is brute-force cosine similarity against all known `Identity` embeddings; a hit above `REID_MATCH_THRESHOLD` appends a `Sighting` and updates the identity's stored embedding via Ultralytics' own `smooth_feature` exponential-moving-average helper (the same function BoT-SORT uses to keep a track's appearance feature stable), a miss creates a new `Identity`.

**Consequences**: `ultralytics` is already a dependency of the detection service and covers detector, tracker, and now re-id encoder with one library, so this adds no new ML framework. The reid service's own new dependencies are `onnxruntime` (runs the `.onnx` reid asset through `AutoBackend`, replacing what would otherwise be a hand-rolled ONNX inference loop), `onnx` (silences a metadata-validation auto-install `AutoBackend` otherwise attempts at every startup), and `lap` (the same linear-assignment solver ADR-0007 already added to detection, needed here only because importing `ultralytics.trackers.utils.reid` pulls in the tracker package's `__init__`); all small, CPU-only, and standard companions to `ultralytics` rather than a second ML stack. The nano ReID variant keeps inference CPU-fast, matching the Phase 1 CPU-only constraint. Embedding only the single best-confidence crop per track, instead of averaging over the whole track, is a known simplification: noisier on tracks where that one frame has partial occlusion or a bad pose; the upgrade path is averaging (or EMA-smoothing via the same `smooth_feature` helper) over multiple sampled crops per track if single-crop match accuracy proves insufficient against docs/PRD.md §9's precision/recall target. Brute-force comparison against every known identity is fine at expected identity counts and matches docs/ARCHITECTURE.md §5's explicit note that an ANN/index structure is a later concern, not a Phase 3 one. Embeddings are stored per `Identity` in the metadata store (Postgres, ADR-0002) as biometric-like data (docs/ARCHITECTURE.md §6); they are never exposed by the REST API, only derived fields (ids, timestamps, match confidence).

## How to add an ADR

Copy the format above. Number sequentially (`ADR-0001`, `ADR-0002`, ...). Status starts as *Proposed* until agreed, then *Accepted* (or *Rejected*, left in the log either way, since rejected paths are useful context for whoever asks "why not X" later).
