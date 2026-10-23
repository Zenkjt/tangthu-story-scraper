# Story Manifest Store — Phase 1

Adds `story_scraper/core/manifest.py` with `StoryManifestStore`.

It stores one chapter-index manifest per `user_id + story_id`, with only story metadata and chapter metadata/URLs. Runtime state (`target_chapter_number`, `status`, `content_hash`) and chapter content are deliberately excluded.

This phase is intentionally independent: it does not modify `StoryApplication` or `StoryEngine` yet.

Install `manifest.py` at `story_scraper/core/manifest.py` and `test_story_manifest.py` at `tests/test_story_manifest.py`, then run:

```bash
PYTHONPATH=. pytest -v tests/test_story_manifest.py
```
