# CHECKPOINT — 0neStory EPUB v1

Date: 2026-10-22

## Chốt

`StoryEpubSink` là implementation đầu tiên của `EpubSink`.

### Artifact

- File duy nhất: `0neStory.epub`
- Cover source: `assets/0neStory.bmp`
- Cover source chuẩn 480×800.
- EPUB lưu cover dưới dạng JPEG grayscale 480×800.
- `cover.xhtml` hiển thị cover.
- `story.xhtml` chứa thông tin truyện.
- `chapter-N.xhtml` chứa từng chapter.
- NCX/EPUB3 navigation được tạo lại sau mỗi append/replace.
- Chapter order theo số chapter.

### Update semantics

- `append()` thêm chapter mới.
- `replace()` thay nội dung chapter hiện có.
- EPUB được ghi qua temporary file rồi atomic replace.
- Story state JSON vẫn là nguồn sự thật; EPUB chỉ là artifact.

### Test

`tests/test_story_epub.py` kiểm tra:
- create;
- append;
- replace;
- chapter order;
- cover 480×800.

## Next

1. Upload `assets/0neStory.bmp`.
2. Upload `story_scraper/story_epub.py`.
3. Replace `requirements-story-scraper.txt`.
4. Upload `tests/test_story_epub.py`.
5. Run CI.
6. Sau khi unit test pass: chạy live Engine + real EPUB end-to-end.
