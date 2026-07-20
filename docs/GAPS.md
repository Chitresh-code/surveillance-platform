# Production Gaps

Phase 4 (docs/PRD.md §10) closes out the PRD's original scope: ingestion, tracking, re-id, the full API surface, the map UI, an API collection, Docker. That scope was never meant to be a production-ready system by itself, it's the demo-able core. This doc tracks what's known to be missing between "the PRD is done" and "this could actually run as a production surveillance platform," so the gaps don't get lost between conversations.

This is a backlog, not a committed roadmap like docs/PRD.md §10. Pulling an item here into a real phase means writing an ADR first if it needs a stack choice (per CLAUDE.md), same as any other phase.

## 1. No auth, API or UI — fixed

**Gap**: The API had no token checking at all; `CORSMiddleware` was wide open. There was no login in the map UI either. docs/DECISIONS.md ADR-0010 closes this: `POST /auth/login` issues a JWT against a new `operators` table, and a `current_operator` FastAPI dependency gates every other endpoint, enforced once in `services/api/api/main.py` rather than per-route. The map UI now has a `/login` route (`frontend/src/Login.tsx`) and redirects there when unauthenticated or when a request 401s. docs/DECISIONS.md ADR-0013 closes the two gaps ADR-0010 deliberately left open: `POST /auth/login` also returns a 7-day refresh token (`POST /auth/refresh` renews the access token without re-entering credentials, `POST /auth/logout` revokes it early), and `/auth/login` is now rate limited (10 failed attempts / 5 minutes, per IP and per username, Redis-backed).

**Why it matters**: This was the gap everything else sat behind. Every identity's movement history, every camera's `stream_url`, every merge/split correction was readable and writable by anyone on the network.

**Next step**: No self-service signup exists (see item 2 for operator account management, which is otherwise now closed). No password complexity rules. Deactivating an operator (item 2) doesn't revoke that operator's already-issued access or refresh tokens immediately, only blocks new logins/refreshes past that point — bounded by the access token's 12h TTL, not instant.

## 2. No management dashboard — mostly fixed

**Gap**: Camera registration, stream start/stop, and identity merge/split only existed as raw API calls (curl/Bruno). `POST /identities/{id}/merge` and `/split` are explicitly "operator correction" endpoints per docs/API_SPEC.md §3, they exist *for* a human, and now have one: `frontend/src/CamerasPage.tsx` (register/edit/delete, stream start/stop) and `frontend/src/IdentitiesPage.tsx` (sightings review, merge/split/delete) are real screens, plus `frontend/src/AuditLogPage.tsx` for the read side of item 7. Operator account management (`POST/GET /operators`, `DELETE /operators/{id}` to deactivate) is now a real API, not just the `api.create_operator` CLI script — no dashboard screen calls it yet, though.

**Why it matters**: Nobody could actually operate this system without reading the API spec and writing curl commands. The whole point of FR-6 (operator corrections) is a human catching a bad match, which requires a UI to review sightings in the first place.

**Next step**: An operator-management *screen* (the API exists, docs/API_SPEC.md's Operators section) is the one piece left, and wasn't built since it wasn't asked for alongside the API this time.

## 3. UI is map-only, no landing page or navigation — fixed

**Gap**: ADR-0009 deliberately scoped the frontend to a single map view with no router: "if the UI grows beyond a map and a couple of list views... this ADR gets revisited with a router." ADR-0010 did exactly that, for auth: `react-router-dom` routes between `/login` and the authenticated screens. `frontend/src/Shell.tsx` is now the shared nav/shell item 2's screens needed: a sidebar with Map/Cameras/Identities/Audit log links, the operator's username, a logout button, and a persistent live-feed panel (item 5), wrapping every authenticated route.

**Why it matters**: A camera list, an identity review screen, and a map are three screens minimum, and they need one consistent place to switch between them from.

**Next step**: None; this closes once item 2's screens existed to nav between.

## 4. No frame/embedding retention or garbage collection — fixed

**Gap**: FR-10 already requires "a configurable retention window on stored video and metadata," and the Privacy NFR (docs/PRD.md §7) says retention limits "must be enforceable, not just advisory," but nothing implemented it. The `frame-store` Docker volume and the `Identity`/`Sighting`/`Detection` tables grew forever. docs/DECISIONS.md ADR-0011 closes this: a new `services/retention` container runs a GC pass on a schedule (`RETENTION_DAYS`, global, default 90), deleting identities/tracks/detections and their frame crop files once they're past the window.

**Why it matters**: Storage cost is the PRD's own called-out concern (§7: "raw video is the dominant storage cost"), and unbounded retention of biometric-like data is also the core of item 7 below (privacy/compliance): this isn't just an ops nuisance.

**Next step**: Retention is global-only for now, not per-camera (docs/PRD.md §11's per-camera half is still open, revisit if a real deployment needs it). Video segments themselves aren't retained yet at all (only frame crops), so there's nothing there for GC to prune until that's built.

## 5. No real-time push or alerting — fixed

**Gap**: The map UI polled `/map/activity` every 10s (ADR-0009) with nothing pushing sooner. docs/PRD.md §4 explicitly called real-time push alerting a non-goal for now: "reasonable follow-on once events are flowing reliably, not part of this scope." Events have been flowing reliably since Phase 3. docs/DECISIONS.md ADR-0012 closes this: `reid` publishes each new sighting to a Redis pub/sub channel, and the API's new `GET /events/stream` (SSE) forwards it to connected clients; the frontend's `LiveFeed` panel (`frontend/src/LiveFeed.tsx`, in the shared `Shell`) shows it as a scrolling log on every authenticated screen.

**Why it matters**: "A known identity reappeared" is a core surveillance use case, and polling can't deliver it promptly or efficiently at any real camera count.

**Next step**: This is a live *feed*, not alerting — no rule engine decides "notify someone when identity X shows up on camera Y." That's a separate, later decision if it's ever needed. `/map/activity`'s poll is unchanged; the SSE feed is additive since the map still needs a full snapshot on load.

## 6. No CI — fixed

**Gap**: docs/TESTING.md §4 already specifies CI expectations (unit+integration on every PR, pipeline/contract tests on merge to main). `.github/workflows/test.yml` covers unit+integration tests (matrix over `services/*`, every PR and push to `main`), pipeline/replay tests (`tests/pipeline`, docs/TESTING.md layer 3: the real YOLO detector, BYTETracker, and ReID encoder — not the mocked models the unit-test layer deliberately uses — against synthetic, not real-footage, frames), and contract tests (docs/TESTING.md layer 4: the `bruno/` collection, via the `bru` CLI with `res.status` assertions added to every request, run against a real docker-compose stack seeded with fixture rows). The latter two are gated to push-to-`main` only, not every PR — real model downloads and a full stack bring-up are too slow for the per-PR loop (docs/TESTING.md §4 explicitly allows this). `.github/workflows/security.yml` (docs/DECISIONS.md ADR-0011) adds static security scanning (CodeQL, Dependency Review) on every PR, free on this repo's public GitHub tier.

**Why it matters**: The part that mattered day to day, a PR silently breaking another service's tests, is closed. Security scanning catches a class of bug the test suite doesn't (known-vulnerable dependencies, common Python security anti-patterns). Pipeline/replay tests catch a class of bug the mocked unit tests structurally can't (a real `ultralytics`/`onnxruntime` API break, a missing model asset, an output-shape mismatch); contract tests catch the collection and docs/API_SPEC.md drifting apart in a way no per-service test suite would notice.

**Next step**: None open. Contract-test assertions check status codes, not full response-body shape — a deeper per-field contract check is a possible future tightening, not a gap that was asked for here.

## 7. No privacy/compliance controls — partially fixed

**Gap**: This system stores face/body embeddings and cross-camera movement history for identifiable people, with no consent flow. docs/PRD.md §7's Privacy NFR names the requirement. Three of four pieces are done: the audit-log write piece (docs/DECISIONS.md ADR-0010, who queried which identity/sighting, written on `identity.get`/`list_sightings`/`merge`/`split`/`delete`), a deletion path (docs/DECISIONS.md ADR-0011): `DELETE /identities/{identity_id}` lets an operator erase one identity's data on demand, and the same logic runs automatically once an identity ages past the retention window (item 4); and the audit-log *read* piece: `GET /audit-log` and `frontend/src/AuditLogPage.tsx` mean it's no longer write-only.

**Why it matters**: Called out in the PRD itself as the one requirement that "must be restricted... not just advisory." For a system that fingerprints people's movements, this is the gap most likely to cause real harm or legal exposure if it ships without it.

**Next step**: A consent/enrollment flow is the remaining piece and needs its own design pass — nothing here gates *collecting* someone's data on their consent, only what happens to it afterward.

## 8. No observability — partially fixed

**Gap**: docs/PRD.md §7's Observability NFR calls for "enough logging/metrics to tell where a given sighting came from and why a match was made" at every pipeline stage. docs/CODING_STANDARDS.md §6 sets a structured-logging convention, and services do log, but nothing aggregates it, and there's no metrics/tracing. `GET /health` (docs/DECISIONS.md ADR-0011) now checks all three dependencies the API actually needs (metadata store, Redis, frame store — the `api` container now mounts the `frame-store` volume read-only just for this), not only the metadata store: `{"status": "ok"}` / 200 when all three round-trip cleanly, `{"status": "degraded", "checks": {...}}` / 503 (still wired up as the `api` container's Docker healthcheck) otherwise.

**Why it matters**: There's no way to tell, today, whether `detection` is silently falling behind on a camera's frame rate, or whether a `reid` match was a near-miss or a confident hit, without reading raw container logs by hand. `/health` now answers "is everything the API itself depends on reachable," a step past "is the API process up," but still nothing about the other services (`detection`, `reid`, `ingestion`) or their throughput.

**Next step**: Metrics/log aggregation is a bigger, genuinely optional-for-now piece — a new dependency (Prometheus/Grafana or similar) and its own ADR, not attempted here; worth revisiting once there's more than one deployment to operate.

## Related, already fixed

Local camera testing (using a phone or laptop webcam instead of a real RTSP camera to develop/demo against) came up alongside this list but isn't a production gap, it's a dev-experience item, and it's resolved: see "Testing with your own camera" in README.md. `services/ingestion/ingestion/capture.py`'s `resolve_capture_source` now treats an all-digit `stream_url` as a local device index instead of only ever treating it as a URL/filename.
