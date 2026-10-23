# CHECKPOINT — Adapter Coverage Phase 5

## Status
Phase 5 hoàn tất. Workflow GitHub xanh toàn bộ **12/12 tests**.

## Mục tiêu
Bổ sung cơ chế coverage toàn cục cho adapter resolution:
- Known Good
- Known Failure
- Unknown
- Failure-first resolution để tránh probe/network không cần thiết.

## Kiến trúc đã chốt

### 1. Resolution Store là global
Không thuộc user/story.

Lưu lịch sử resolution theo domain:
- `domain`
- `adapter`
- `result`
- `reason`
- `timestamp`

Lưu cả success và failure.

### 2. Coverage hiện hành
`AdapterResolutionStore.coverage(domain)` lấy record mới nhất:

- `success` → **Known Good**
- `failure` → **Known Failure**
- chưa có record → **Unknown**

Lịch sử cũ không bị xóa.

### 3. Failure-first
Khi nhận URL:

```text
Known Failure
    ↓
trả lỗi ngay
    ↓
KHÔNG probe/network adapter
```

### 4. Known Good
Domain đã từng resolve thành công:
- adapter thành công trước đó được ưu tiên;
- vẫn verify bình thường.

### 5. Unknown
Nếu chưa có coverage:
```text
VnThuQuan
    ↓ reject
Wattpad
    ↓ reject
StaticHTMLFamily
    ↓
success / failure
```

Thứ tự thực tế vẫn do Adapter Registry priority quyết định.

### 6. Failure → Success
Nếu domain đang có failure nhưng sau này resolution thành công:
- success mới trở thành trạng thái active;
- domain trở thành Known Good;
- failure cũ vẫn giữ trong history.

## Reason taxonomy

- `HTTP_403`
- `HTTP_404`
- `HTTP_5XX`
- `TIMEOUT`
- `DNS_ERROR`
- `BLOCKED_OR_CHALLENGE`
- `PARSE_ERROR`
- `NO_STORY_METADATA`
- `NO_CHAPTER_LINKS`
- `INVALID_CHAPTER_URL`
- `UNSUPPORTED_STRUCTURE`
- `ADAPTER_NOT_APPLICABLE`
- `NO_MATCHING_ADAPTER`
- `UNKNOWN_ERROR`

`ADAPTER_NOT_APPLICABLE` chỉ có nghĩa adapter không phù hợp; không phải website failure thực sự.

## Test coverage

Workflow hiện tại chạy:

1. `tests/test_story_manifest.py` — **2/2**
2. `tests/test_application_manifest_integration.py` — **2/2**
3. `tests/test_story_catalog.py` — **2/2**
4. `tests/test_adapter_resolution.py` — **6/6**

**Tổng: 12/12 PASS.**

## Commit / workflow
Phase 5 đã được commit. Workflow dùng chung:

`.github/workflows/manifest-store-test.yml`

Không tạo workflow riêng.

## Điểm chưa triển khai
Known Failure hiện là fast-path. Nếu sau này thêm adapter mới cho một domain đang nằm trong failure coverage, cần có cơ chế **recheck/force recheck** để adapter mới có cơ hội chạy.

Đây là phần mở rộng tương lai, chưa thuộc Phase 5.

## Checkpoint
Phase 5 hoàn tất và có thể chuyển sang phase kiến trúc tiếp theo.
