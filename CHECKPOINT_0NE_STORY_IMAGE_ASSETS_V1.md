# Checkpoint — 0neStory image assets v1

## Chốt

`0neStory.epub` now supports chapter-local image assets without changing the Engine's one-trigger/one-chapter rule.

### Flow

`Adapter -> ChapterContent(html + assets) -> Engine -> StoryEpubSink -> EPUB`

- `ChapterContent` carries HTML plus binary `ChapterAsset` objects.
- `ChapterContent.fingerprint()` hashes both HTML and asset bytes, so an image-only update also triggers chapter replacement.
- `BaseStaticHTMLAdapter` detects `src`, `data-src`, `data-original`, and `data-lazy-src` on `<img>` elements.
- Images are downloaded by the adapter and rewritten to EPUB-local paths such as `images/chapter-1-001.jpg`.
- `StoryEpubSink` embeds those assets into the EPUB.
- Existing plain-string chapter content remains supported.
- VnThuQuan is the first adapter wired for image extraction.

## Deliberate scope

- No image deduplication across chapters yet.
- No CSS background-image extraction.
- Failed image downloads are skipped rather than failing the whole chapter.
- Existing page links/navigation remain as-is.
