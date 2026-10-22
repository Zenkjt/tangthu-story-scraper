# Checkpoint — Registry Source Integration V1

## Status
Adapter Registry 17/17 tests are green.

## Decision
The registry now exposes `resolve_source(url)`, which returns:

- the `Story` produced by `build_index()`
- the exact same adapter instance that built that `Story`

This prevents the application from resolving/instantiating an adapter twice.

## Flow

```text
URL
 ↓
AdapterRegistry.candidates()
 ↓
priority / explicit rejection fallback
 ↓
one adapter instance
 ↓
adapter.build_index()
 ↓
ResolvedStorySource(adapter, story)
 ↓
StoryEngine(..., adapter)
```

## Important rule
Only `AdapterNotApplicable` triggers fallback. Network, HTTP, parser and other real errors continue to propagate.

## Public helpers
- `build_story_source(url)` → `ResolvedStorySource`
- `build_story_index(url)` → `Story` compatibility helper

## Next step
After this test is green in GitHub Actions, integrate this source-resolution path into the real application/trigger entry point. Do not modify the Wattpad or VnThuQuan adapters.
