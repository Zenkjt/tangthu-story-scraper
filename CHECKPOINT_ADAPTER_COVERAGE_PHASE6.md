# CHECKPOINT — Adapter Coverage Phase 6

## Status
Phase 6 implemented: manual GitHub Actions recheck of the active Failure List.

## Chốt kiến trúc
- Runtime request vẫn giữ failure-first: domain đang Failure trả lỗi ngay, không probe/network.
- Không tạo public `force_recheck` endpoint.
- Recheck chỉ là maintenance workflow nội bộ.
- Workflow đọc toàn bộ active Failure List.
- Mỗi failure phải có URL lịch sử để recheck chính xác.
- Recheck bypass failure fast-path.
- Success: ghi record success mới → domain tự động trở thành Known Good và biến mất khỏi active Failure List.
- Failure: ghi failure mới → domain tiếp tục nằm trong active Failure List.
- Không xóa history cũ.
- Nếu record cũ không có URL (trước Phase 6), workflow skip domain đó và báo trong log.

## Thay đổi
1. `story_scraper/core/resolution.py`
   - Resolution record lưu thêm `url` (backward-compatible với record cũ).
   - Coverage trả lại URL.
2. `story_scraper/core/registry.py`
   - `resolve_source()` giữ nguyên behavior runtime.
   - thêm maintenance-only `recheck_source()` để bypass active failure fast-path.
   - mọi resolution record mới lưu URL.
3. `scripts/recheck_adapter_coverage.py`
   - quét toàn bộ active Failure List.
   - recheck từng URL.
   - tổng hợp checked/success/still_failed/skipped.
4. `.github/workflows/recheck-adapter-coverage.yml`
   - `workflow_dispatch`, chỉ chạy thủ công, không chạy tự động.
   - chạy script và commit resolution history nếu có thay đổi.
5. `tests/test_adapter_resolution.py`
   - kiểm tra URL được lưu.
   - kiểm tra recheck bypass failure.
   - kiểm tra recheck thất bại vẫn giữ active failure.

## Vận hành
Sau khi thêm adapter mới:
`GitHub → Actions → Recheck Adapter Coverage → Run workflow`

Workflow sẽ thử lại toàn bộ domain đang Failure; không cần chỉ định từng domain.
