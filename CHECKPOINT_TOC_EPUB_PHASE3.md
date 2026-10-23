# STORY SCRAPER — TOC EPUB PHASE 3

Date: 2026-10-23

## Decision

`0neStoryTOC.epub` is the navigation/index EPUB for one user/story.

It contains:
- cover
- story title
- author
- discovered chapter list
- source URL for each chapter

It contains **no chapter content**.

## Data ownership

- Manifest = per-user/per-story chapter index cache.
- Story State = current target chapter and runtime state.
- `0neStory.epub` = downloaded chapter content only.
- `0neStoryTOC.epub` = navigation/index only.

## Integration

`StoryApplication` accepts an optional `StoryCatalogEpubSink` and passes it to
`StoryEngine`.

The existing engine already calls:
- `catalog.create(story)` on initialization.
- `catalog.update(story)` after a trigger.

Therefore a trigger that discovers new tail chapters updates the TOC EPUB
without downloading those new chapters.

## Invariant

One normal trigger still fetches exactly one chapter.
