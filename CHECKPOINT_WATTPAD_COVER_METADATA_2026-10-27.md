# CHECKPOINT — Wattpad cover metadata

Date: 2026-10-27

## Decision

Wattpad cover is already requested by the existing story metadata API call:

`GET /api/v3/stories/{story_id}?fields=...,cover`

Therefore Tàng Thư must **not** make a second API request just to retrieve the cover.

## Implementation

1. `story_scraper/core/models.py`
   - Add `Story.cover_url`.
   - Persist it in `as_dict()` / restore it in `from_dict()`.
   - Field is appended at the end to preserve existing positional constructor compatibility.

2. `story_scraper/adapters/platforms/wattpad.py`
   - Preserve the existing API response field `data["cover"]` into `Story.cover_url`.

3. `scripts/run_story_request.py`
   - Change only the existing `cache_cover()` assignment:
     `cover_url = story.cover_url or discover_cover_url(story.source_url)`
   - This makes API metadata the preferred source.
   - Existing HTML `og:image` / Twitter metadata remains fallback for adapters that do not provide `cover_url`.

## Intentionally not changed

- No second Wattpad API call.
- No changes to chapter fetching.
- No changes to TOC behavior.
- No changes to EPUB logic.
