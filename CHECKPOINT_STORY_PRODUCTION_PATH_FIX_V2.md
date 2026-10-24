# Checkpoint — Story Production Path Fix V2
Date: 2026-10-24

## Chốt
1. `story_id` không được dùng trực tiếp làm tên/path filesystem vì có thể chứa `/`.
2. Runtime state dùng filename đã sanitize: `<safe_story_id>.json`.
3. `0neStory.epub` và `0neStoryTOC.epub` không chứa cover.
4. Cover không còn là điều kiện bắt buộc của production path.
5. GitHub cache chỉ lưu metadata/TOC/state của story; không lưu chapter content.
6. `0neStory.epub` vẫn là artifact nội dung trên Drive.

## File thay thế
- `story_scraper/core/state.py`
- `story_scraper/story_catalog.py`
- `story_scraper/story_epub.py`
- `scripts/run_story_request.py`

## Lưu ý
Bộ này là file thay thế hoàn chỉnh, không cần chạy patch trên GitHub Web.
