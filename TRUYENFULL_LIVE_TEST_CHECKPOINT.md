# TruyenFull live test checkpoint — 2026-10-22

## Result so far

`StaticHTMLFamilyAdapter` successfully indexed:

- URL: `https://truyenfull.live/than-dao-dan-ton-6060282/`
- Title: `Thần Đạo Đan Tôn`
- Discovered chapters: 5343
- Chapter range: 1 → 5357, with gaps
- Chapter URLs resolve to `/chuong-N/`
- Index discovery completed without fetching chapter content

The generic static-HTML family adapter therefore recognizes the TruyenFull pagination/index model without a dedicated TruyenFull adapter.

## Next test

Verify the lazy-fetch contract end-to-end:

1. Build the index.
2. Initialize `StoryEngine` and `StoryEpubSink`.
3. Trigger once.
4. Fetch exactly chapter 1.
5. Create `0neStory.epub` containing chapter 1 only.
6. Verify chapter 2 is absent.
7. Verify the target advances to chapter 2.

## Architectural conclusion if this passes

TruyenFull can be served by the existing generic `StaticHTMLFamilyAdapter`; no dedicated TruyenFull adapter is justified at this stage.

The expensive pagination crawl belongs to index/manifest construction, not to the per-chapter download trigger.
