# Coding Standards

These are the conventions for this repo, independent of whichever languages/frameworks end up in each service (tracked in docs/DECISIONS.md). Update this doc when a convention actually changes in practice — don't let it drift into aspirational fiction.

## 1. Repository layout

```
surveillance-platform/
├── docs/                 # this doc set
├── services/
│   ├── ingestion/
│   ├── detection/
│   ├── reid/
│   └── api/
├── frontend/             # map UI
├── postman/              # API collection, kept in sync with docs/API_SPEC.md
├── docker/                # shared docker/compose assets
├── docker-compose.yml
└── README.md
```

Each service under `services/` is self-contained: its own dependency manifest, its own tests, its own Dockerfile. Shared code between services only gets pulled into a common package once at least two services actually need it — not in anticipation of a third.

## 2. Commits & branches

- Commit messages: `type(scope): one line summary` — e.g. `feat(reid): add cosine similarity matcher`, `docs(api): document merge endpoint`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Scope is the service or doc area touched.
- Branch names: `type/short-title` — e.g. `feat/reid-matcher`, `fix/track-timeout`, `docs/api-auth-section`. Same `type` values as commits.
- Keep commits scoped to one logical change. A docs update and a code change are two commits, not one.

## 3. Pull requests

- One PR per feature or fix, small enough to review in one sitting. If a PR description needs a table of contents, it's too big.
- PR description states *why*, not a restatement of the diff — the diff already shows what changed.
- A PR that touches `docs/API_SPEC.md` and adds/changes an endpoint must update `postman/` in the same PR.
- No PR merges with failing tests or with a new dependency that isn't justified in the description.

## 4. Naming & readability

- Names describe what something is or does, not how it's implemented (`active_cameras`, not `camera_list_2`).
- Small functions with one job. If you need a comment to explain what a block does, it's usually a sign to extract it into a named function instead.
- No dead code, no commented-out blocks, no `TODO` without an owner and a reason it can't be done now.
- Comments explain *why*, never *what* — the code already says what. Don't write a comment restating a function's signature or a docstring that just repeats the parameter names.

## 5. Error handling

- Fail loudly at service boundaries (API requests, external stream connections, DB writes). No silent `except: pass`.
- Internal pipeline errors (e.g., one bad frame) should not take down a worker — log it with enough context to find the frame/track/camera, and move on. A single malformed frame is not a reason to drop a camera's whole session.
- API error responses always use the envelope defined in docs/API_SPEC.md §5.

## 6. Logging

- Structured (key-value or JSON), not free-text string concatenation.
- Every log line inside the pipeline includes the relevant `camera_id` and `track_id` (or `identity_id`) so an event can be traced end to end.
- Never log raw frame bytes, embeddings, or full video paths at anything above debug level.

## 7. Configuration

- Config comes from environment variables, not hardcoded values or committed config files with real endpoints/credentials.
- No secrets in the repo, ever — not in code, not in commit history, not in a "temporary" config file. `.env.example` documents required keys with placeholder values.

## 8. Dependencies

- Reach for the standard library or an already-used dependency before adding a new one.
- A new dependency needs a one-line justification in the PR description: what it replaces, why the alternative wasn't enough.
- Pin versions. No floating `*` or `latest` in a manifest that ships.

## 9. Testing

See docs/TESTING.md for strategy. In short: new logic ships with tests in the same PR, not as a follow-up.
