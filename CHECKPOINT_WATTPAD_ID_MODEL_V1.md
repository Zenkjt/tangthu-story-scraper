# CHECKPOINT — Wattpad ID model V1

## Decision

Wattpad story ID and part/chapter ID are separate identifiers.

- Story URL `/story/107024873-...` -> `story_id = 107024873`
- Chapter URL `/402782528-...-chuong-1` -> `external_id = 402782528`

The universal `Chapter` model now carries `external_id` separately from the
sequential `number` used by the Story Engine.

## Why

Platform IDs are not chapter numbers. The Engine must operate on a stable
sequential chapter position while adapters preserve the platform's native ID.

Unicode/percent-encoded Vietnamese slugs are retained in the source URL and
are not used as identifiers.

## Scope of this checkpoint

This package adds the Wattpad URL/manifest model and tests. It does NOT yet
implement live Wattpad HTTP/API resolution. That is intentionally the next
probe step.
