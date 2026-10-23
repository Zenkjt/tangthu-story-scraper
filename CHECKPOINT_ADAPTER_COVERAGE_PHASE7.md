# CHECKPOINT — Adapter Coverage Phase 7

## Status
Phase 7 hoàn tất về kiến trúc.

## Quyết định
Adapter registration không chứa danh sách domain.

Mỗi adapter chỉ cần khai báo:
- `name`
- `family`
- `priority`
- `matches/probe`
- các phương thức xử lý story/chapter.

Domain coverage được học từ resolution thực tế.

## Registry
`AdapterRegistry` nay cung cấp:
- `registered_adapters()`
- `registered_adapter_names()`

Việc thêm adapter mới không cần sửa một danh sách domain riêng.

## Coverage
`AdapterResolutionStore` suy ra coverage hiện hành từ resolution history:
- `active_coverage()`
- `known_good_list()`
- `failure_list()`
- `coverage_for_adapter(adapter)`

Failure cũ vẫn giữ trong history; success mới nhất quyết định trạng thái active.

## Recheck
Phase 6 vẫn là cơ chế cập nhật coverage sau khi thêm adapter:
- workflow thủ công;
- recheck toàn bộ Active Failure List;
- success → Good;
- failure → tiếp tục Failure.

## Test
Thêm test bảo đảm:
1. adapter registration không cần domain list;
2. coverage được suy ra từ resolution history.

## Next
Có thể chuyển sang phase tiếp theo sau khi workflow test xanh.
