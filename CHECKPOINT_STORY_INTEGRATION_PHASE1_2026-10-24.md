# CHECKPOINT — STORY INTEGRATION PHASE 1 — 2026-10-24

## Đã chốt

Luồng Story chuyển sang kiến trúc bất đồng bộ, cùng mô hình với News Worker:

`Tàng Thư UI`
→ `tangthu-story-worker`
→ `tangthu-story-scraper/story-cache/requests/<request_id>.json`
→ `repository_dispatch: story-request`
→ `tangthu-story-scraper` GitHub Action
→ `StoryApplication`
→ cập nhật cache / operation.

Worker không scrape, không build EPUB, không ghi Google Drive.

## API

POST:
- `/story/register`
- `/story/next`
- `/story/previous`
- `/story/jump`

POST trả `202 + request_id`.

GET:
- `/story/operation?request_id=...`
- `/story/current?user_id=...&story_id=...`
- `/story/sources`

## Cache

Cache nằm trong `tangthu-story-scraper`:

```text
story-cache/
├── requests/
├── story-sources.json
└── <user>/<story_id>/
    └── story.json
```

`story.json` chỉ metadata + chapter index + runtime state nhẹ.
Không lưu chapter content và không lưu EPUB.

## Drive

Runner đã chuẩn bị đường gọi:
- đọc `0neStory.epub` bằng Google Drive API;
- ghi `0neStory.epub` qua Apps Script `upload_epub`.

Nhưng Apps Script hiện tại đang allowlist một folder cố định và chỉ `0neNews.epub`.
Cần áp dụng patch `ADD_STORY_UPLOAD_SUPPORT.md` để cho phép folder đã đăng ký và:
- `0neNews.epub`
- `0neStory.epub`
- `0neStoryTOC.epub`

## GUI

`postprocess_story.py` đã chuyển sang async polling:
- POST action → nhận `request_id`
- polling `/story/operation`
- khi completed nhận `operation.story`.

## Chưa triển khai production

Chưa deploy Worker và chưa commit workflow/runner vào `tangthu-story-scraper`.
