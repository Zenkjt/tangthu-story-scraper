# Tàng thư Story Scraper — Core State Fix v3
Date: 2026-10-21

## Chốt
Thay `current_index` bằng `target_chapter_number`.

## Quy tắc
- Một trigger = đúng một chapter fetch.
- OPEN giữ nguyên target và trigger sau fetch lại.
- COMPLETE chuyển sang chapter kế tiếp đã biết.
- Xử lý chapter cuối → chỉ refresh tail.
- Re-index không làm mất content_hash/trạng thái download.
- Previous chỉ đổi target, không fetch ngay.
- Hỗ trợ số chapter không liên tục.

## Tương thích
`Story.from_dict()` đọc được state cũ dùng `current_index`.

## Bước kế
Chạy test toàn bộ rồi mới làm platform-family adapter thật.
