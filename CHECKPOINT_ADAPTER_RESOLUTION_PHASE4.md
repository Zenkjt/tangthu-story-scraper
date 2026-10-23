# ADAPTER RESOLUTION REGISTRY — PHASE 4

Date: 2026-10-23

## Decision

Introduce a **global Adapter Resolution Registry/Cache** independent of
user/story state.

It records both successful and failed adapter-resolution attempts so the
system accumulates evidence about domains and adapter compatibility.

## Record

Each record contains:

- `domain`
- `adapter`
- `result` (`success` / `failure`)
- `reason`
- `timestamp`

Storage is append-only JSONL.

## Failure reasons

The first implementation recognizes:

- `HTTP_403`
- `HTTP_404`
- `HTTP_5XX`
- `TIMEOUT`
- `DNS_ERROR`
- `BLOCKED_OR_CHALLENGE`
- `PARSE_ERROR`
- `NO_STORY_METADATA`
- `NO_CHAPTER_LINKS`
- `INVALID_CHAPTER_URL`
- `ADAPTER_NOT_APPLICABLE`
- `NO_MATCHING_ADAPTER`
- `UNKNOWN_ERROR`

## Resolution behavior

1. A cached successful adapter is prioritized for the same domain.
2. The adapter is still actually executed; cache is only a resolution hint.
3. `AdapterNotApplicable` is recorded and fallback continues.
4. Real network/parser errors are recorded and re-raised.
5. No matching adapter records `NO_MATCHING_ADAPTER`.

The existing fallback invariant is preserved:
**only `AdapterNotApplicable` triggers adapter fallback.**

## Scope

This cache is global/system-level, not per-user and not per-story.

## Configuration

`build_application(..., resolution_root=...)` creates the global store and
passes it to the default registry.

No change is made to the ownership model:

- Manifest = per-user/per-story chapter index.
- Story State = runtime target/state.
- `0neStory.epub` = chapter content.
- `0neStoryTOC.epub` = navigation/index.
- Adapter Resolution Registry = global adapter telemetry/history.

## Tests

Phase 4 adds three tests:

- rejection + success are both recorded;
- real failures are recorded and re-raised;
- cached successful adapter is prioritized.

## Invariant

One normal trigger still fetches exactly one chapter.
