# CHECKPOINT — ONE STORY REGISTRATION STARTS FROM PASTED CHAPTER

## Decision

When a user registers a story using a Wattpad chapter URL, registration uses that
chapter as the initial download target.

### Registration flow

1. Parse the pasted URL.
2. If it is a chapter URL, resolve the chapter `part_id`.
3. Use Wattpad Part API to obtain `group.id` and identify the parent `story_id`.
4. Fetch the parent Story API for whole-book metadata and the complete chapter list.
5. Build Tàng Thư's TOC from the actual story chapters; the introduction/preface
   is metadata only and is not included as a TOC entry.
6. Renumber Tàng Thư TOC from 1:
   - `1. Chương 1`
   - `2. Chương 2`
   - ...
7. Set `target_toc_index` to the chapter represented by the pasted URL.
8. During the same registration action, fetch exactly that target chapter.
9. Create `0neStory.epub` and immediately append the fetched chapter.
10. If the chapter is complete, advance `target_toc_index` to the next known
    TOC entry. If incomplete, keep the same target so the next trigger retries it.

## Result

- Pasting chapter 2 creates a readable `0neStory.epub` containing chapter 2.
- The EPUB TOC still represents the whole known book.
- Chapters before the registration point are not downloaded automatically.
- No second trigger is required to obtain the first readable content.
- A failed initial chapter fetch must not leave an empty `0neStory.epub`.

## Implementation

`story_scraper/core/engine.py::StoryEngine.initialize()` performs the initial
fetch and writes the first chapter.

The Wattpad adapter already resolves a chapter URL to its parent story through
the chapter's `group.id`, then fetches the parent story metadata and parts.
