# Checkpoint — Unified Story Navigation Pipeline
Date: 2026-11-08

## Decision
Next, Previous and Jump use one production navigation pipeline:
1. Resolve a canonical 1-based `toc_index`.
2. Set target where required.
3. Fetch the selected entry through `StoryApplication.trigger_next()`.
4. Rebuild `0neStory.epub`.
5. Persist StoryState to Apps Script cache.
6. Upload `0neStory.epub`; upload `0neStoryTOC.epub` only if TOC changed.
7. Mark the request operation completed and refresh source coverage.

## Previous semantics
Previous targets the entry immediately before `current_toc_index`, not the entry before `target_toc_index`. After a successful Next, target commonly points one entry ahead, so using target would reload the currently displayed entry.

Previous at the first TOC entry, or with no current entry, returns a validation error without fetching or publishing.

## Jump contract
Jump uses `toc_index` end-to-end. `chapter_number` is not accepted as the canonical request field because source chapter numbers and Tàng Thư TOC positions are different concepts.

## Files changed
- `tangthu-story-scraper/scripts/run_story_request.py`
  - Added `resolve_navigation_target()`.
  - Added shared `execute_navigation()` pipeline.
  - Replaced separate Previous/Next/Jump execution branches with one shared call.
- `tangthu-story-scraper/tests/test_navigation_pipeline.py`
  - Added target resolution, edge-case and shared-pipeline tests.
- `tangthu-story-worker/src/index.js`
  - Changed Jump request validation and request payload from `chapter_number` to `toc_index`.
- `tangthu-opds/scripts/postprocess_story.py`
  - Changed GUI prompt and payload to TOC position / `toc_index`.

## Compatibility / rollout
Deploy in this order:
1. `tangthu-story-scraper` (runner + tests).
2. `tangthu-story-worker`.
3. Rebuild and deploy `tangthu-opds` so the GUI sends `toc_index`.

The existing request queue and `repository_dispatch` event remain unchanged. No legacy CrossPoint ingress routes were removed.

## Validation
- Python syntax compilation is required for changed Python files.
- Run `pytest -q tests/test_navigation_pipeline.py` in the repository environment after dependencies are installed.
- Run the existing full test suite before production deployment.
- This workspace did not have `ebooklib` installed, so runtime pytest execution could not be completed here.
