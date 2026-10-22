# Checkpoint — Application Entry Point V1

## Status
Adapter Registry + Source Integration: green at 18/18 tests.

## Decision
Introduce a thin `StoryApplication` layer as the real application entry point.

It is intentionally not a web server, CLI, or plugin endpoint yet. It centralizes the transition:

```text
URL
 ↓
AdapterRegistry.resolve_source()
 ↓
ResolvedStorySource
 ├── Story
 └── adapter instance
       ↓
StoryEngine
       ↓
state + EPUB
```

## Operations

- `initialize(url, epub)`
  - resolves the URL through Registry
  - builds the story index
  - passes the exact same adapter instance to `StoryEngine.initialize()`

- `trigger_next(story_id, epub)`
  - loads persisted state
  - resolves an adapter from the stored source URL
  - triggers exactly one chapter

- `trigger_previous(story_id, epub)`
  - loads persisted state
  - resolves an adapter
  - changes only the target; does not fetch

## Important
A new adapter instance on a later trigger is intentional: the process may be restarted between triggers. The important invariant is that the initialization path does not instantiate a second adapter after `build_index()`.

## Next step
Run the application-entrypoint regression tests. If green, this layer becomes the single place for future CLI/web/plugin trigger wiring. Then proceed to the first true family adapter.
