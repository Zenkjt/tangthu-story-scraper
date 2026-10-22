# CHECKPOINT — Registry canonical adapter imports

Date: 2026-10-22

## Problem verified
The public package `story_scraper.adapters` imported Wattpad from the older
stub `story_scraper/adapters/wattpad.py`, whose `build_index()` raises
`NotImplementedError`. The implemented adapter lives in
`story_scraper/adapters/platforms/wattpad.py`.

The Registry's `default_registry()` imports from `story_scraper.adapters`, so
the old package export could route a matching Wattpad URL to the stub.

## Fix
- Export `WattpadAdapter` from `story_scraper.adapters.platforms.wattpad`.
- Keep `VnThuQuanAdapter` from its existing platform module.
- Add `resolve_instance(url)` so the application can obtain a concrete adapter.
- Add a regression assertion that the default registry returns the implemented
  Wattpad adapter class.

## Next after this passes
Integrate `resolve_instance(url)` with story initialization so the exact same
adapter instance is used for indexing, StoryEngine chapter fetch, and tail
refresh. Then add the first true family adapter (static HTML) and test it on
a second site, without weakening Wattpad/VnThuQuan URL matching.
