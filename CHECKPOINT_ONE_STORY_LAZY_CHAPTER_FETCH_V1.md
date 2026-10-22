# Checkpoint — 0neStory Lazy Chapter Fetch V1

## Chốt kiến trúc

- **Index/discovery chỉ lấy danh sách chapter**: number, title, URL, external ID nếu adapter có.
- Pagination chỉ được dùng để đi qua các **trang danh sách chương**.
- Không tải nội dung chapter trong `build_index()` hoặc `refresh_tail()`.
- Không lưu chapter-content cache.
- **Mỗi trigger fetch đúng 1 chapter** bằng `fetch_chapter()`.
- Nếu chapter OPEN: trigger kế tiếp fetch lại chính chapter đó và replace nếu fingerprint thay đổi.
- Nếu chapter COMPLETE: chuyển target sang chapter kế tiếp đã biết.
- Nếu vừa xử lý chapter cuối đã biết: refresh index để phát hiện chapter mới, nhưng **không fetch chapter mới trong cùng trigger**.
- `jump_to_chapter(N)` chỉ đổi target, không download.

## Navigation EPUB

Sinh thêm một EPUB nhẹ dành cho navigation:

- tên truyện
- bìa
- metadata cơ bản
- TOC toàn bộ chapter đã biết
- không chứa nội dung chapter

File này được cập nhật khi manifest thay đổi. Nó không phải content cache.

## Nguyên tắc tài nguyên

Index pages có thể được fetch khi discovery/refresh, nhưng HTML chỉ tồn tại tạm trong memory. Chapter content chỉ được fetch tại thời điểm trigger.
