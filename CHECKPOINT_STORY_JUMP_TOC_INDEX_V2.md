# Checkpoint — Story Jump theo đúng thứ tự TOC

**Date:** 2026-10-25  
**Repository:** `Zenkjt/tangthu-story-scraper`  
**Target:** `scripts/run_story_request.py`

## Quyết định đã chốt

`Jump` nhận **số thứ tự trong TOC**, không nhận `chapter.number` của nguồn.

Ví dụ:

- TOC #15 = `Chương 14`
- Người dùng nhập `15`
- Hệ thống phải **tải ngay entry TOC #15**, tức `Chương 14`
- Sau khi tải xong, GUI vẫn phải hiển thị vị trí hiện tại là **#15**, không tự nhảy sang #16.

## Nguyên nhân lỗi

Luồng hiện tại dùng `app.set_target(..., toc_index)` rồi `app.trigger_next()`.
`trigger_next()` tải đúng entry được target, nhưng sau khi tải thành công nó tự tiến `target_toc_index` sang entry kế tiếp. Vì vậy GUI hiển thị #16 dù EPUB vừa tải là #15.

## Cách sửa

Sau `trigger_next()`:

1. Giữ identity ổn định của entry được yêu cầu trước khi fetch.
2. Tìm lại entry đó sau fetch bằng `external_id` → URL → `(kind, number)` → fallback.
3. `set_target()` về đúng entry vừa tải.
4. Không thay đổi logic `Next` / `Previous`.
5. Không wrap ở đầu/cuối TOC.

Identity được dùng để chịu được trường hợp tail refresh làm thay đổi thứ tự/`toc_index`.

## Phạm vi

Chỉ sửa `scripts/run_story_request.py`.
Không sửa engine, adapter, schema TOC hay workflow.

## Kiểm thử mong đợi

- Jump `15` → tải TOC #15 → GUI hiện #15.
- Nếu TOC #15 là `Chương 14` → EPUB là `Chương 14`.
- Next sau Jump #15 → đi #16.
- Previous sau Jump #15 → đi #14.
- Jump #1 → tải entry #1 và vẫn hiện #1.
- Jump entry cuối → tải entry cuối và vẫn hiện entry cuối.
- Không có vòng #1 ↔ cuối.
