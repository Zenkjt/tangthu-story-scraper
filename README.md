# tangthu-story-api-phase1

Phase 1 foundation for the Story Worker/API.

The design follows the existing News Worker pattern:
- Cloudflare Worker = HTTP API/orchestration.
- GitHub repository = persistent Story metadata/TOC cache.
- Story Scraper = actual crawling/EPUB work, triggered asynchronously.

The Story cache stores metadata, TOC URLs, lightweight state and the original cover.
It does not store chapter content.

Do not deploy this phase yet: Drive EPUB delivery and the Story GitHub Action are
the next integration step.
