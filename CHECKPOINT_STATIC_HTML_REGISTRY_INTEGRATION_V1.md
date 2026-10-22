# Checkpoint — Static HTML Family Registry Integration V1

Date: 2026-10-22

## Decision

`StaticHTMLFamilyAdapter` is now part of the canonical default adapter registry.

Resolution order:

1. Exact platform adapter — priority 100
2. Static HTML family adapter — priority 50
3. Future generic fallback adapters — lower priority

The family adapter remains a conservative fallback. It does not replace or modify the existing Wattpad/VnThuQuan exact adapters.

## Changes

- Exported `StaticHTMLFamilyAdapter` from `story_scraper/adapters/__init__.py`.
- Added `StaticHTMLFamilyAdapter` to `default_registry()`.
- Added regression coverage proving:
  - generic HTTP URLs can resolve to the static HTML family;
  - Wattpad remains ahead of the family adapter;
  - explicit adapter rejection still permits fallback;
  - real adapter errors still propagate;
  - resolved source keeps the adapter instance used to build the story.

## Expected validation

Run:

`PYTHONPATH=. pytest -v tests/test_adapter_registry.py tests/test_application.py tests/test_static_html_family.py`

Then run the existing full regression workflows.

## Next architectural step

After this checkpoint is green, move to the next platform-family adapter only when a real target site requires a materially different protocol/structure.
