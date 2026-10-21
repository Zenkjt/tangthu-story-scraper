# Tàng thư Story Scraper Core

Core riêng của Tàng thư, lấy ý tưởng adapter/chapter manifest/update từ FanFicFare nhưng không phụ thuộc FanFicFare.

## Adapter architecture

```text
SiteAdapter
    │
    └── BasePlatformAdapter
            │
            ├── BaseStaticHTMLAdapter
            │       ├── vnthuquan / eFiction-like sites
            │       └── other static HTML families
            │
            └── custom platform bases
                    └── WattpadAdapter / site-specific adapters
```

### Phân tầng

- `SiteAdapter`: contract tối thiểu mà Story Engine cần.
- `BasePlatformAdapter`: cơ chế dùng chung giữa các adapter cùng họ nền tảng: URL normalization, dedupe, chapter-number parsing, chapter merge.
- `BaseStaticHTMLAdapter`: transport/parsing boundary cho nhóm site lấy dữ liệu chủ yếu từ HTML.
- Site-specific adapter: chỉ chứa selector/API và quy tắc riêng của site.

## Core rules

- Một trigger = đúng một chapter fetch.
- Chapter `OPEN` được fetch lại ở trigger kế tiếp; nếu nội dung đổi thì replace trong EPUB.
- Chapter `COMPLETE` mới cho phép tiến sang chapter tiếp theo.
- Khi hết chapter đã biết mới `refresh_tail()`; không crawl lại toàn bộ story.
- Re-index không được làm mất `content_hash` hoặc trạng thái đã download.
- Core không biết selector, endpoint hay HTML đặc thù của từng site.
- Adapter không sở hữu state EPUB.

## Thứ tự adapter

`SiteDetector` dùng thứ tự đăng ký. Adapter đặc thù phải đứng trước adapter family rộng hơn để tránh family adapter bắt URL trước.

## Chưa làm

- Wattpad extraction thật.
- eFiction/vnthuquan family adapter thật.
- HTTP transport production.
- EPUB implementation.
- Web trigger/API.
- CrossPoint plugin.
