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

## ADR-0009: Map UI frontend stack: React + Vite + Leaflet

**Status**: Accepted

**Context**: Phase 4 (docs/PRD.md §10) builds the Map UI (docs/ARCHITECTURE.md §1: "a client of the REST API, nothing more. Renders camera locations and recent sightings"). docs/ARCHITECTURE.md §7 leaves the frontend framework and map library unpinned, and docs/CODING_STANDARDS.md §1 already reserves `frontend/` for it. No frontend code exists yet, so there's no lock-in to work around.

**Decision**: React + TypeScript, built with Vite, mapping via Leaflet through `react-leaflet` (the standard React binding for Leaflet, not a separate library decision). The UI calls the REST API directly (`GET /map/cameras`, `GET /map/activity`) with no server-side rendering and no state-management library beyond React's own hooks.

**Consequences**: React is the most common choice for this kind of small, component-driven read-only dashboard, so onboarding and examples are cheap to find; Vite gives fast local dev/build with near-zero config, avoiding hand-rolled bundler setup. Leaflet is a small, dependency-light map library with no API key or paid tier required, matching the API-client-only role docs/ARCHITECTURE.md assigns the UI. `react-leaflet` trades a small extra dependency for idiomatic React markers/popups instead of imperative DOM calls inside `useEffect`. This is a client-only app: it holds no state beyond what the API returns on each poll/fetch, so there's no data layer to design beyond a thin fetch wrapper. If the UI grows beyond a map and a couple of list views (auth, routing across multiple pages, complex client state), this ADR gets revisited with a router and/or state library; neither is justified yet.

## ADR-0010: Auth: JWT bearer tokens, operator accounts, and an audit log

**Status**: Accepted

**Context**: docs/GAPS.md item 1 flagged this as the gap everything else sits behind: no endpoint checked a token, `CORSMiddleware` was wide open, and docs/API_SPEC.md §7 had carried "auth scheme: not yet decided" since Phase 4. docs/PRD.md §11 posed the open question as "operator accounts vs. API keys vs. both." Separately, docs/GAPS.md item 7 (no privacy/compliance controls) named an audit log of who queried which identity as its smallest, most immediately doable piece, one that becomes free once requests carry a caller identity. ADR-0009 (the frontend stack) already named "auth" and "routing across multiple pages" as its own explicit trigger to be revisited.

**Decision**: One mechanism for every caller, UI and integrator alike: `POST /auth/login` takes a username/password, checks it against a new `operators` table (bcrypt-hashed passwords), and returns a signed JWT (`pyjwt`, HS256, 12h expiry, no refresh token). Every other endpoint requires `Authorization: Bearer <token>`, enforced once via a `current_operator` FastAPI dependency attached to each router's `include_router(..., dependencies=[...])` call in `services/api/api/main.py`, not per-route. The token's claims (operator id, username) are trusted directly without a DB round-trip per request, since the signature is the trust boundary. A new `audit_log` table records `identity.get`, `identity.list_sightings`, `identity.merge`, and `identity.split` actions with the acting operator's id, satisfying docs/GAPS.md item 7's audit piece as a side effect of having a caller identity on every request. Operator accounts have no self-service signup; the first (and any subsequent) operator is created with a CLI script, `uv run python -m api.create_operator <username> <password>` (`services/api/api/create_operator.py`), the same "run a module directly" pattern the README already uses for `ingestion.main`. On the frontend, this triggers ADR-0009's own revisit clause: `react-router-dom` is added for a `/login` route and a guard around the existing map view, and `vitest`/`@testing-library/react` are added since the auth-header/login logic is the frontend's first security-relevant code path and none of that test tooling existed before.

**Consequences**: One enforcement path instead of two (no separate API-key scheme for integrators; an integrator logs in the same way an operator does) is less code and less surface area, at the cost of no scoped/read-only integrator credentials yet, if that's ever needed, it's a new token type layered on the same `current_operator` dependency, not a rewrite. No refresh token means a session hard-expires at 12h with no silent renewal; acceptable for an operator tool, revisit if that proves annoying in practice. No password complexity rules, no rate limiting on `/auth/login`, and no operator deactivation/management UI: none of that was asked for and docs/GAPS.md item 2 (a management dashboard) already tracks operator management as its own, separate, not-yet-built piece. `bcrypt` and `pyjwt` are new dependencies (`services/api/pyproject.toml`); neither existed anywhere in the repo before (checked: no `jose`/`passlib`/`hashlib`-based auth code existed). CORS stays wide open (`allow_origins=["*"]`): bearer tokens aren't attached automatically by the browser cross-origin the way cookies are, so this doesn't reopen a CSRF hole, only a session-cookie scheme would need that tightened. Audit logging is scoped to identity reads/corrections only, not every list/browse endpoint, since that's what docs/GAPS.md item 7 actually asked for; broader request logging is a separate, larger observability concern (docs/GAPS.md item 8).

## ADR-0011: Retention/GC, identity deletion, `/health`, and CI security scanning

**Status**: Accepted

**Context**: Four docs/GAPS.md items were picked up together as one batch: item 4 (no frame/embedding retention or GC — FR-10 and docs/PRD.md §7's Privacy NFR both require an enforceable retention window; docs/ARCHITECTURE.md §6 already says this "must be enforced by a scheduled process, not left as a manual cleanup task"), item 6 (CI has no security scanning), item 7 (no on-demand deletion path for an identity's data, the second half of the audit-log work ADR-0010 started), and item 8 (no `/health` endpoint, called out there as "nearly free"). docs/PRD.md §11 left "video retention default (days) and whether it's per-camera or global" open.

**Decision**: One global `RETENTION_DAYS` env var (default 90), not per-camera — the per-camera half of PRD §11's question is deferred until something actually needs it. A new `services/retention` container runs a GC pass every `RETENTION_GC_INTERVAL_SECONDS` (default 24h): `common/retention.py`'s `gc_expired` deletes identities whose `last_seen` is older than the cutoff, cascading to their sightings, tracks, detections, and frame crop files (`Detection.frame_path`, already an absolute path under the shared `frame-store` volume per ADR-0006), plus any track that never matched an identity at all (no `Sighting`) once it's older than the cutoff on its own. This cascade-delete logic lives in `services/common` because two services need it: the retention container's scheduled GC, and a new `DELETE /identities/{identity_id}` endpoint on the API (audit-logged as `identity.delete`) that lets an operator erase one identity's data on demand — docs/GAPS.md item 7's remaining "deletion path" piece, reusing the same primitive rather than writing it twice. `GET /health` is a new, unauthenticated endpoint (infra doesn't carry an operator's bearer token) doing a single `SELECT 1` against the metadata store, registered outside `/api/v1` since it isn't a versioned resource; `docker-compose.yml`'s `api` service now uses it as its Docker healthcheck. CI gains `.github/workflows/security.yml`: GitHub's own CodeQL (Python) plus `actions/dependency-review-action`, both free on a public repo, run on every PR alongside the existing test workflow.

**Consequences**: A new always-on container (`retention`) rather than piggybacking the GC loop onto an existing service, more to deploy, but its schedule's lifecycle stays independent of a request-serving process (the API) or a stream-processing one (detection/reid). GC judges a track's age by whether it's still unmatched (no `Sighting`) or by its identity's `last_seen`, not by individual detection timestamps — a long-lived track with an old first frame but a recent last frame isn't touched, since it isn't stale by either measure; frame-level pruning independent of track/identity age isn't built, revisit this ADR if that turns out to matter. No consent/enrollment flow and no self-service (non-operator-initiated) deletion request exist yet, those stay open per docs/GAPS.md item 7; this ADR only closes "an operator can delete an already-known identity's data now, and it happens automatically once it's old enough." `/health` checks DB connectivity only, not Redis or the frame store, enough to answer "is the API up and can it reach its database," not a full dependency health check. `actions/dependency-review-action` only runs on `pull_request` since it diffs two refs; CodeQL runs on both PR and push to `main`.

## ADR-0012: Real-time sighting feed: Redis pub/sub + Server-Sent Events

**Status**: Accepted

**Context**: docs/GAPS.md item 5 named the map UI's 10s poll (ADR-0009) as unable to deliver "a known identity reappeared" promptly at any real camera count, and noted the Phase 4 non-goal on real-time push (docs/PRD.md §4) no longer holds now that events flow reliably (Phase 3+). This was picked up alongside item 2 (management dashboard) and item 7's remaining audit-log read gap as one batch.

**Decision**: `reid` publishes a small JSON message (`identity_id`, `camera_id`, `track_id`, `seen_at`, `match_confidence`) to a Redis pub/sub channel (`sightings`) immediately after committing each `Sighting` in `services/reid/reid/worker.py`. This reuses the same Redis instance ADR-0005 already put in the stack rather than adding a new broker; a pub/sub channel is a separate concern from that ADR's `tracks:ready` stream (fire-and-forget fan-out to whoever's listening now, not a durable/replayable queue — a client that isn't connected when a sighting happens simply misses it, no different from a poll interval it happened to fall between). The API adds `GET /events/stream`, unauthenticated by FastAPI's normal `current_operator` dependency (`EventSource` can't set an `Authorization` header) but instead checked via a `token` query-string param decoded with the same JWT logic as every other endpoint; it subscribes to the `sightings` channel and forwards each message as an SSE `data:` line for as long as the client stays connected. The frontend live-feed panel opens one `EventSource` per session instead of polling.

**Consequences**: A dropped connection or a moment where nothing is subscribed loses that sighting from the live feed; the feed is a "what's happening now" convenience, not an audit trail (the `Sighting` row and `audit_log` table remain the durable record, queried via the existing paginated endpoints). Token-in-query-string is weaker than a header (it can land in server access logs); acceptable here since the token already carries only a 12h-lived claim and this repo has no scoped/read-only token type to reach for instead (ADR-0010's own noted gap). `/map/activity`'s poll stays as-is for the map view; the SSE feed is additive, not a replacement, since the map still needs a full snapshot on load, not just a delta stream.

## ADR-0013: Refresh tokens and login rate limiting

**Status**: Accepted

**Context**: ADR-0010 deliberately shipped without either: "no refresh token means a session hard-expires at 12h... revisit if that proves annoying in practice" and "no rate limiting on `/auth/login`... none of that was asked for." docs/GAPS.md item 1 tracked both as the auth gap's remaining piece; this ADR supersedes those two specific consequences of ADR-0010 (the rest of ADR-0010 — JWT bearer tokens, the `current_operator` dependency, the audit log — stands unchanged).

**Decision**: `POST /auth/login` now returns both the existing 12h JWT access token and a new opaque refresh token (`secrets.token_urlsafe(32)`, 7 day TTL). The refresh token is stored server-side as a SHA-256 hash (not bcrypt: this is a high-entropy random value, not a low-entropy user password, so it needs a fast lookup hash, not a slow one) in a new `refresh_tokens` table, so a leaked DB dump doesn't hand over live sessions. `POST /auth/refresh` exchanges a valid, unexpired, unrevoked refresh token for a new access token *and* a new refresh token, revoking the old one (rotation) — reuse of an already-rotated refresh token is a signal of theft, so it's rejected the same as an expired one, distinguishing the two isn't done yet. `POST /auth/logout` revokes a refresh token on demand (sets `revoked_at`), closing the loop rotation opens: a refresh mechanism without a revoke path can't actually terminate a session early. `POST /auth/login` also gains a fixed-window rate limit, checked before touching the password hash: 10 failed attempts per 5 minutes per client IP *and* per username (whichever trips first), tracked as Redis `INCR`+`EXPIRE` counters (reusing ADR-0005's Redis instance, no new dependency) and incremented only on a failed attempt. Both limits exist together deliberately — per-IP alone is porous behind shared NAT/CGNAT (many legitimate users, one IP), per-username alone doesn't stop a single source spraying guesses across many accounts.

**Consequences**: Access-token behavior is unchanged (still a 12h bearer JWT, still trusted without a DB round-trip per ADR-0010) — this is additive, not a rewrite: a client that ignores the refresh token entirely still works exactly as before until the 12h mark. Deactivating an operator (docs/GAPS.md item 2) still doesn't revoke an already-issued *access* token (unchanged from ADR-0010), but now at least bounds a compromised session harder: an operator's refresh tokens aren't auto-revoked on deactivation either (a known gap — deactivation blocks new logins and any refresh past that point fails since a per-refresh operator `is_active` check isn't implemented, only login checks it today; revisit if immediate hard-revocation on deactivation matters in practice). Rate-limit counters are per-process-independent (Redis-backed, correct across multiple `api` replicas) but are an availability control, not a cryptographic one — an attacker distributed across enough IPs and usernames isn't meaningfully slowed; that's the accepted ceiling for a fixed-window counter, the upgrade path is a real WAF/edge rate limiter if this is ever internet-facing rather than an internal operator tool. No password complexity rules still isn't addressed (out of scope for this ADR). The refresh token is a bearer credential same as the access token: a client stores it the same way (frontend: alongside the access token per ADR-0010's client, `localStorage`) and it must be treated with the same care.

## How to add an ADR

Copy the format above. Number sequentially (`ADR-0001`, `ADR-0002`, ...). Status starts as *Proposed* until agreed, then *Accepted* (or *Rejected*, left in the log either way, since rejected paths are useful context for whoever asks "why not X" later).
