# STORY SCRAPER — MANIFEST INTEGRATION PHASE 2

Date: 2026-10-23

## Implemented

- `StoryApplication` now receives `StoryManifestStore`.
- First initialization builds the source index once and saves it per user/story.
- Later triggers load the manifest instead of rebuilding the full story index.
- Runtime state remains in `StoryStateStore`.
- Manifest contains chapter metadata only.
- Existing stories without a manifest are migrated from existing state without crawling again.

## Data ownership

- Manifest = chapter index/source metadata.
- Story State = current target chapter and runtime chapter state.
- `0neStory.epub` = downloaded chapter content.
- `0neStoryTOC.epub` = navigation/index EPUB; implementation comes next.

## Invariant

One normal trigger still fetches exactly one chapter.
