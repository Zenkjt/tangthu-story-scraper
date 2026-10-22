# CHECKPOINT — Adapter Registry / Fallback V1

Date: 2026-10-22

## Chốt
Story Scraper dùng Adapter Registry theo thứ tự:
1. Exact platform/domain adapter
2. Platform-family adapter
3. Generic adapter

Một URL có thể có nhiều candidate; Registry thử theo priority.

## Fallback
Chỉ `AdapterNotApplicable` mới cho phép chuyển sang adapter kế tiếp.
Lỗi mạng/HTTP/parser thật phải propagate, không được nuốt để fallback giả.

## Hai adapter hiện tại
- WattpadAdapter: exact platform adapter.
- VnThuQuanAdapter: exact platform adapter; có thể chứa nhiều domain của VnThuQuan.

Hai adapter này không biến thành generic adapter. Registry chỉ chọn chúng khi `matches()/probe()` xác nhận URL thuộc platform đó.

## Mở rộng
Sau này thêm family adapters như:
- Static HTML story family
- API story family
- Manga/comic family

Family adapter có thể probe cấu trúc site rồi raise `AdapterNotApplicable` nếu không phù hợp.

## Phạm vi
Checkpoint này chưa nối Registry vào StoryEngine/plugin/Drive và chưa triển khai generic scraping.
