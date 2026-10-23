# CHECKPOINT — PHASE 9: GUI Story / Bookshelf Registration

## Status
Implemented Phase 9 GUI workflow baseline.

## Chốt
- User registers a receiving folder before story controls become active.
- Registration button sits beside the receiving-folder field.
- Bookshelf name is derived from the registered folder and persisted in `.tangthu-bookshelf.json`.
- `0neStory.epub` and `0neStoryTOC.epub` are fixed output names in the registered bookshelf.
- First story registration resolves the URL, builds the index, and fetches exactly one initial chapter.
- Empty story URL resumes the registered story without re-indexing.
- A new URL while a story is registered requires confirmation before replacement.
- Navigation (`Lùi`, `Tiến`, `Nhảy chương`) changes target only; `Tải chương` is the explicit one-chapter fetch action.
- Any chapter URL can be used for first registration; if its chapter number is recognized by the built manifest, that chapter becomes the initial target.
- State/manifest are stored under the bookshelf's `.tangthu/` directory; adapter-resolution history remains global under the user's home `.tangthu/resolution/` directory.
