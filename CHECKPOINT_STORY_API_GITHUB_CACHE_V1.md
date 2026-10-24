# CHECKPOINT — Story API + GitHub Story Cache v1

Date: 2026-10-24

## Chốt

Story dùng cùng mô hình Worker/API như News.

### Persistent cache trên GitHub

Lưu:
- metadata truyện
- TOC/chapter index: number, title, URL, external_id nếu có
- current target / trạng thái nhẹ
- ảnh bìa gốc

Không lưu:
- nội dung chapter
- ảnh/assets trong chapter
- EPUB

### Luồng

```text
tangthu-opds
    |
    | HTTPS
    v
tangthu-story-worker
    |
    +--> GitHub Story Cache
    |
    +--> repository_dispatch
              |
              v
      tangthu-story-scraper
```

Worker không crawl chapter.

Các thao tác scrape/build chạy bất đồng bộ qua GitHub Action. Web đọc lại trạng thái
từ `/story/current`.

## API

- GET  /story/current?user_id=...&story_id=...
- POST /story/register
- POST /story/next
- POST /story/previous
- POST /story/jump

## Cover

Giữ ảnh bìa gốc trong cache để cửa sổ “Đăng ký đọc online” trên Tàng thư hiển thị.

## Chưa làm trong phase này

- GitHub Action thực thi StoryApplication
- ghi EPUB vào Google Drive
- upload cover binary
- operation status/polling đầy đủ
- atomic/concurrency retry hoàn chỉnh

Các phần này là phase kế tiếp, không giả định chúng đã tồn tại.
