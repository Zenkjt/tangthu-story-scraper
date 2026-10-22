# TruyenFull Live Application Pipeline Checkpoint

## Goal
Verify TruyenFull through the existing Tàng thư application pipeline, not a parallel engine/test path.

## Required pipeline

```text
TruyenFull URL
    -> StoryApplication / AdapterRegistry
    -> VnThuQuanAdapter rejects
    -> StaticHTMLFamilyAdapter accepts
    -> build_index() discovers chapter manifest only
    -> StoryApplication.initialize()
    -> StoryEngine
    -> one trigger fetches exactly one chapter
    -> existing StoryEpubSink creates 0neStory.epub
```

## Test assertions
- Story title is `Thần Đạo Đan Tôn`.
- Chapter 1 is the initial target.
- `trigger_next()` is called through `StoryApplication`, not directly on `StoryEngine`.
- Chapter 1 is present in the EPUB.
- Chapter 2 is absent from the EPUB.
- Target advances to chapter 2 after chapter 1 completes.

## Architectural decision
Do not create a TruyenFull-specific adapter unless the generic `StaticHTMLFamilyAdapter` fails on a structural/protocol difference. TruyenFull is currently treated as a validation case for the existing static-HTML family pipeline.
