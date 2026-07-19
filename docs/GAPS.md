# Production Gaps

Phase 4 (docs/PRD.md §10) closes out the PRD's original scope: ingestion, tracking, re-id, the full API surface, the map UI, Postman, Docker. That scope was never meant to be a production-ready system by itself, it's the demo-able core. This doc tracks what's known to be missing between "the PRD is done" and "this could actually run as a production surveillance platform," so the gaps don't get lost between conversations.

This is a backlog, not a committed roadmap like docs/PRD.md §10. Pulling an item here into a real phase means writing an ADR first if it needs a stack choice (per CLAUDE.md), same as any other phase.

## 1. No auth, API or UI

**Gap**: The API has no token checking at all; `CORSMiddleware` is wide open (`allow_origins=["*"]`). docs/API_SPEC.md §7 already flags this as an open item ("assume every endpoint requires a bearer token... until it lands"), but nothing enforces it. There's no login in the map UI either: it's a static bundle, anyone who can reach it can reach the API behind it.

**Why it matters**: This is the gap everything else sits behind. Every identity's movement history, every camera's `stream_url` (which can embed credentials), every merge/split correction is readable and writable by anyone on the network. Blocks real deployment outright, not a polish item.

**Next step**: ADR for the auth mechanism (bearer token / API key for integrators, session-based login for the UI; docs/PRD.md §11 already poses this as "operator accounts vs. API keys vs. both"). Enforced once, as a FastAPI dependency, not per-route. Do this first: items 2 and 3 below are pointless to build behind an open door.

## 2. No management dashboard

**Gap**: Camera registration, stream start/stop, and identity merge/split only exist as raw API calls (curl/Postman). `POST /identities/{id}/merge` and `/split` are explicitly "operator correction" endpoints per docs/API_SPEC.md §3, they exist *for* a human, but there's no screen for that human.

**Why it matters**: Nobody can actually operate this system without reading the API spec and writing curl commands. The whole point of FR-6 (operator corrections) is a human catching a bad match, which requires a UI to review sightings in the first place.

**Next step**: Camera CRUD screen, stream start/stop controls, and an identity review screen (sightings list + merge/split actions) in `frontend/`. Depends on item 1 (auth) and item 3 (routing) landing first.

## 3. UI is map-only, no landing page or navigation

**Gap**: ADR-0009 deliberately scoped the frontend to a single map view with no router: "if the UI grows beyond a map and a couple of list views... this ADR gets revisited with a router." It just did, per item 2.

**Why it matters**: A camera list, an identity review screen, and a map are three screens minimum. Without a router and a shell (nav, layout), each new screen becomes its own bolted-on special case.

**Next step**: Add a router (React Router is the obvious default, but this is a real ADR-0009 revision, not a given) and a shared app shell once item 2's screens are actually being built, not before.

## 4. No frame/embedding retention or garbage collection

**Gap**: FR-10 already requires "a configurable retention window on stored video and metadata," and the Privacy NFR (docs/PRD.md §7) says retention limits "must be enforceable, not just advisory," but nothing implements it. The `frame-store` Docker volume and the `Identity`/`Sighting`/`Detection` tables grow forever.

**Why it matters**: Storage cost is the PRD's own called-out concern (§7: "raw video is the dominant storage cost"), and unbounded retention of biometric-like data is also the core of item 7 below (privacy/compliance): this isn't just an ops nuisance.

**Next step**: A retention-window config (per docs/PRD.md §11, per-camera or global, still open) plus a GC job that deletes frame crops and DB rows past the window. Needs a decision on whether it's a cron-style job in an existing service or a new one.

## 5. No real-time push or alerting

**Gap**: The map UI polls `/map/activity` every 10s (ADR-0009). docs/PRD.md §4 explicitly calls real-time push alerting a non-goal for now: "reasonable follow-on once events are flowing reliably, not part of this scope." Events have been flowing reliably since Phase 3.

**Why it matters**: "A known identity reappeared" is a core surveillance use case, and polling can't deliver it promptly or efficiently at any real camera count.

**Next step**: Worth revisiting the Phase 4 non-goal now that it's true. Smallest version: a webhook/SSE feed off the same event stream the API already reads from Sighting; alerting rules (which identity, which camera) are a separate, later decision.

## 6. No CI

**Gap**: docs/TESTING.md §4 already specifies CI expectations (unit+integration on every PR, pipeline/contract tests on merge to main), but no GitHub Actions workflow (or equivalent) actually runs them. Every test run in this project so far has been manual, `uv run pytest` by hand, per service.

**Why it matters**: Nothing currently stops a PR that breaks another service's tests from merging. This gets worse, not better, the longer it's deferred, and it's cheap relative to everything else on this list.

**Next step**: A workflow per docs/TESTING.md §4's own layers: unit+integration per service on every PR (matrix over `services/*`), pipeline/replay and contract (`postman/` via `newman`) tests on merge to `main`.

## 7. No privacy/compliance controls

**Gap**: This system stores face/body embeddings and cross-camera movement history for identifiable people, with no consent flow, no audit log of who queried which identity, and no data-deletion path beyond raw SQL. docs/PRD.md §7's Privacy NFR names the requirement; nothing implements it yet.

**Why it matters**: Called out in the PRD itself as the one requirement that "must be restricted... not just advisory." For a system that fingerprints people's movements, this is the gap most likely to cause real harm or legal exposure if it ships without it, ahead of most items above on actual risk, even though it's not blocking day-to-day development the way auth is.

**Next step**: An audit log table (who queried which identity/sighting, when) is the smallest piece and layers on top of item 1 (auth) for free once there's a caller identity to log. Consent/enrollment flow and a deletion API are bigger and need their own design pass, likely alongside item 4 (retention).

## 8. No observability

**Gap**: docs/PRD.md §7's Observability NFR calls for "enough logging/metrics to tell where a given sighting came from and why a match was made" at every pipeline stage. docs/CODING_STANDARDS.md §6 sets a structured-logging convention, and services do log, but nothing aggregates it, there's no metrics/tracing, and the API has no `/health` endpoint.

**Why it matters**: There's no way to tell, today, whether `detection` is silently falling behind on a camera's frame rate, or whether a `reid` match was a near-miss or a confident hit, without reading raw container logs by hand.

**Next step**: `/health` on the API is nearly free (checks DB connectivity) and worth doing regardless of what comes next. Metrics/log aggregation is a bigger, genuinely optional-for-now piece; worth revisiting once there's more than one deployment to operate.

## Related, already fixed

Local camera testing (using a phone or laptop webcam instead of a real RTSP camera to develop/demo against) came up alongside this list but isn't a production gap, it's a dev-experience item, and it's resolved: see "Testing with your own camera" in README.md. `services/ingestion/ingestion/capture.py`'s `resolve_capture_source` now treats an all-digit `stream_url` as a local device index instead of only ever treating it as a URL/filename.
