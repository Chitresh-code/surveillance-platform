# CLAUDE.md

Context for working in this repo.

## What this is

A multi-camera surveillance platform: video ingestion, per-camera object detection/tracking, cross-camera re-identification, metadata storage, map visualization, all behind a REST API. Full scope: docs/PRD.md.

## Status

Docs-only phase. No service code exists yet. Don't assume any framework, database, or model is chosen — check docs/DECISIONS.md before writing code that implies a specific one.

## Where to look

- docs/PRD.md — scope, requirements, phased roadmap
- docs/ARCHITECTURE.md — components, data flow, deployment topology (mermaid diagrams)
- docs/API_SPEC.md — REST contract; source of truth over any Postman collection
- docs/CODING_STANDARDS.md — repo layout, commit/branch/PR/logging/error conventions
- docs/DECISIONS.md — ADR log; the only place a technology choice is "decided"
- docs/TESTING.md — test layers and what belongs in each

## Git workflow

- The initial project skeleton (this doc set) is pushed directly to `main` — no PR for that first commit.
- Every change after that goes on a branch (`type/short-title`, see docs/CODING_STANDARDS.md §2) and merges to `main` via PR. Nothing gets pushed to `main` directly once the skeleton is in place.
- Commit messages: `type(scope): one line summary` (docs/CODING_STANDARDS.md §2).

## Rules for this repo

- Don't invent a stack choice. If a task needs one that isn't an Accepted ADR in docs/DECISIONS.md, propose it and add the ADR before writing code that depends on it.
- A change to docs/API_SPEC.md that adds or changes an endpoint must be matched by a `postman/` update in the same change, once that directory exists.
- Follow docs/CODING_STANDARDS.md for layout, naming, commit style, and error handling — it's short, read it rather than guessing conventions.
- New logic ships with a test in the same change (docs/TESTING.md), not as a follow-up.
- Keep docs and code from drifting: if an ADR or the API spec turns out to be wrong once implementation reveals it, update the doc in the same PR, don't leave it stale.
