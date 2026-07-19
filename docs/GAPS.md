# Production Gaps

Phase 4 (docs/PRD.md §10) closes out the PRD's original scope: ingestion, tracking, re-id, the full API surface, the map UI, an API collection, Docker. That scope was never meant to be a production-ready system by itself, it's the demo-able core. This doc tracks what's known to be missing between "the PRD is done" and "this could actually run as a production surveillance platform," so the gaps don't get lost between conversations.

This is a backlog, not a committed roadmap like docs/PRD.md §10. Pulling an item here into a real phase means writing an ADR first if it needs a stack choice (per CLAUDE.md), same as any other phase.

## 1. No auth, API or UI — fixed

**Gap**: The API had no token checking at all; `CORSMiddleware` was wide open. There was no login in the map UI either. docs/DECISIONS.md ADR-0010 closes this: `POST /auth/login` issues a JWT against a new `operators` table, and a `current_operator` FastAPI dependency gates every other endpoint, enforced once in `services/api/api/main.py` rather than per-route. The map UI now has a `/login` route (`frontend/src/Login.tsx`) and redirects there when unauthenticated or when a request 401s.

**Why it matters**: This was the gap everything else sat behind. Every identity's movement history, every camera's `stream_url`, every merge/split correction was readable and writable by anyone on the network.

**Next step**: No self-service signup or operator management exists yet, operators are created with `uv run python -m api.create_operator <username> <password>` (see item 2). No rate limiting on `/auth/login`, no refresh token (a session hard-expires at 12h).

## 2. No management dashboard

**Gap**: Camera registration, stream start/stop, and identity merge/split only exist as raw API calls (curl/Bruno). `POST /identities/{id}/merge` and `/split` are explicitly "operator correction" endpoints per docs/API_SPEC.md §3, they exist *for* a human, but there's no screen for that human. Operator account creation is in the same boat: a CLI script (`api.create_operator`), not a screen.

**Why it matters**: Nobody can actually operate this system without reading the API spec and writing curl commands. The whole point of FR-6 (operator corrections) is a human catching a bad match, which requires a UI to review sightings in the first place.

**Next step**: Camera CRUD screen, stream start/stop controls, an identity review screen (sightings list + merge/split actions), and operator management, in `frontend/`. Its two former blockers, auth and routing, are both in place now (item 1, item 3), so this is unblocked, just not built.

## 3. UI is map-only, no landing page or navigation — partially fixed

**Gap**: ADR-0009 deliberately scoped the frontend to a single map view with no router: "if the UI grows beyond a map and a couple of list views... this ADR gets revisited with a router." ADR-0010 did exactly that, for auth: `react-router-dom` now routes between `/login` and `/` (the map). There's still only one real screen behind the login, item 2's camera/identity/operator screens don't exist yet.

**Why it matters**: A camera list, an identity review screen, and a map are three screens minimum. The router and a `RequireAuth` guard now exist (`frontend/src/App.tsx`), so adding those screens is additive, not a restructure.

**Next step**: Add the screens themselves, and a shared nav/shell once there's more than one authenticated screen to switch between. Tracked as item 2.

## 4. No frame/embedding retention or garbage collection — fixed

**Gap**: FR-10 already requires "a configurable retention window on stored video and metadata," and the Privacy NFR (docs/PRD.md §7) says retention limits "must be enforceable, not just advisory," but nothing implemented it. The `frame-store` Docker volume and the `Identity`/`Sighting`/`Detection` tables grew forever. docs/DECISIONS.md ADR-0011 closes this: a new `services/retention` container runs a GC pass on a schedule (`RETENTION_DAYS`, global, default 90), deleting identities/tracks/detections and their frame crop files once they're past the window.

**Why it matters**: Storage cost is the PRD's own called-out concern (§7: "raw video is the dominant storage cost"), and unbounded retention of biometric-like data is also the core of item 7 below (privacy/compliance): this isn't just an ops nuisance.

**Next step**: Retention is global-only for now, not per-camera (docs/PRD.md §11's per-camera half is still open, revisit if a real deployment needs it). Video segments themselves aren't retained yet at all (only frame crops), so there's nothing there for GC to prune until that's built.

## 5. No real-time push or alerting

**Gap**: The map UI polls `/map/activity` every 10s (ADR-0009). docs/PRD.md §4 explicitly calls real-time push alerting a non-goal for now: "reasonable follow-on once events are flowing reliably, not part of this scope." Events have been flowing reliably since Phase 3.

**Why it matters**: "A known identity reappeared" is a core surveillance use case, and polling can't deliver it promptly or efficiently at any real camera count.

**Next step**: Worth revisiting the Phase 4 non-goal now that it's true. Smallest version: a webhook/SSE feed off the same event stream the API already reads from Sighting; alerting rules (which identity, which camera) are a separate, later decision.

## 6. No CI — partially fixed

**Gap**: docs/TESTING.md §4 already specifies CI expectations (unit+integration on every PR, pipeline/contract tests on merge to main). `.github/workflows/test.yml` now covers the first half: unit+integration tests, matrix over `services/*`, on every PR and on push to `main`. Pipeline/replay and contract tests still aren't wired in, but neither exists in the repo yet either (docs/TESTING.md layers 3 and 4), so there's nothing to run yet. `.github/workflows/security.yml` (docs/DECISIONS.md ADR-0011) adds static security scanning (CodeQL, Dependency Review) on every PR, free on this repo's public GitHub tier.

**Why it matters**: The part that mattered day to day, a PR silently breaking another service's tests, is closed. Security scanning catches a class of bug the test suite doesn't (known-vulnerable dependencies, common Python security anti-patterns). The remaining piece only matters once the pipeline/contract test layers exist.

**Next step**: Add pipeline/replay and contract (`bruno/` via the `bru` CLI) jobs to `.github/workflows/test.yml`, gated on merge to `main` per docs/TESTING.md §4, once those tests themselves are written.

## 7. No privacy/compliance controls — partially fixed

**Gap**: This system stores face/body embeddings and cross-camera movement history for identifiable people, with no consent flow. docs/PRD.md §7's Privacy NFR names the requirement. Two of three pieces are done: the audit-log piece (docs/DECISIONS.md ADR-0010, who queried which identity/sighting, written on `identity.get`/`list_sightings`/`merge`/`split`), and a deletion path (docs/DECISIONS.md ADR-0011): `DELETE /identities/{identity_id}` lets an operator erase one identity's data on demand (audit-logged as `identity.delete`), and the same logic runs automatically once an identity ages past the retention window (item 4).

**Why it matters**: Called out in the PRD itself as the one requirement that "must be restricted... not just advisory." For a system that fingerprints people's movements, this is the gap most likely to cause real harm or legal exposure if it ships without it.

**Next step**: A consent/enrollment flow is the remaining, bigger piece and needs its own design pass. No API endpoint exposes the audit log itself yet either, it's write-only for now.

## 8. No observability — partially fixed

**Gap**: docs/PRD.md §7's Observability NFR calls for "enough logging/metrics to tell where a given sighting came from and why a match was made" at every pipeline stage. docs/CODING_STANDARDS.md §6 sets a structured-logging convention, and services do log, but nothing aggregates it, and there's no metrics/tracing. `GET /health` (docs/DECISIONS.md ADR-0011) now exists: an unauthenticated DB round-trip, wired up as the `api` container's Docker healthcheck.

**Why it matters**: There's no way to tell, today, whether `detection` is silently falling behind on a camera's frame rate, or whether a `reid` match was a near-miss or a confident hit, without reading raw container logs by hand. `/health` only answers "is the API up," not that broader question.

**Next step**: Metrics/log aggregation is a bigger, genuinely optional-for-now piece; worth revisiting once there's more than one deployment to operate. `/health` also only checks the metadata store, not Redis or the frame store.

## Related, already fixed

Local camera testing (using a phone or laptop webcam instead of a real RTSP camera to develop/demo against) came up alongside this list but isn't a production gap, it's a dev-experience item, and it's resolved: see "Testing with your own camera" in README.md. `services/ingestion/ingestion/capture.py`'s `resolve_capture_source` now treats an all-digit `stream_url` as a local device index instead of only ever treating it as a URL/filename.
