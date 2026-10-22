# CHECKPOINT — Adapter Registry wired for story-index creation

Date: 2026-10-22

## Scope
This checkpoint provides a single entry point for resolving a source URL and
building the initial story index through the registered platform adapters.

## Behavior
- `default_registry()` registers `WattpadAdapter` and `VnThuQuanAdapter`.
- `build_story_index(url)` picks candidates by descending `priority`.
- `AdapterNotApplicable` permits trying the next matching candidate.
- Runtime/network/parser failures are propagated and do not silently trigger
  another adapter.
- The registry does not fetch chapter text during `build_index()` unless the
  chosen adapter violates its contract.

## Tests
`tests/test_adapter_registry.py` covers ordering, explicit fallback, runtime
error propagation, and built-in platform matching.
The workflow also runs the existing engine/EPUB/Wattpad/VnThuQuan regression
suites.

## Important boundary
This is not a generic scraper yet. Wattpad and VnThuQuan adapters still match
their own known URL formats. Family-level adapters are a later addition.

## Integration note
`StoryEngine` still receives a concrete `SiteAdapter`; this keeps engine
responsibilities unchanged. Application code should call
`build_story_index(url)`, then pass the returned `Story` and the matching
adapter instance into its normal initialization path. The next integration
step can centralize that factory once the existing runtime/entry point is
identified.
