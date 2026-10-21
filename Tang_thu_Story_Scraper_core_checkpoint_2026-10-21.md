# Tàng thư Story Scraper — Core Checkpoint 2026-10-21

## Chốt sau khi bóc tách FanFicFare

Không đưa FanFicFare vào làm dependency. Chỉ lấy các ý tưởng lõi:

- Site Adapter riêng cho từng website.
- Chapter Index/manifest.
- Story State tách khỏi EPUB.
- Fetch/re-fetch chapter.
- So sánh nội dung chapter đang mở.
- Re-index phần cuối khi hết chapter đã biết.

## Core đã dựng

- `SiteAdapter`
- `SiteDetector`
- `Story`, `Chapter`, `ChapterStatus`
- `StoryStateStore`
- `StoryEngine`
- `EpubSink`
- `WattpadAdapter` skeleton

## Luật engine

### Một trigger = đúng một chapter

Nếu target là chapter đang `open`:

- fetch lại chính chapter đó;
- hash nội dung;
- nếu thay đổi → replace trong EPUB;
- nếu chưa hoàn tất → giữ target.

Nếu chapter hoàn tất:

- đánh dấu `complete`;
- trigger kế tiếp chuyển sang chapter tiếp theo.

Khi xử lý chapter cuối cùng đã biết:

- chỉ refresh tail/index;
- phát hiện chapter mới thì thêm vào state;
- không tự động tải chapter mới.

## Tách state khỏi EPUB

EPUB chỉ là artifact.

State riêng lưu:

- story URL;
- adapter;
- metadata;
- chapter index;
- chapter status;
- content hash;
- current target.

Điều này cho phép engine điều khiển việc update mà không phải dùng EPUB như database.

## Chưa triển khai

- Wattpad extraction thực tế.
- Adapter vnthuquan.
- EpubSink nối vào downloader/EPUB builder hiện có.
- Web trigger.
- CrossPoint plugin.

## Artifact

`tangthu-story-scraper-core.zip`

Đây là skeleton lõi để gắn các phần còn lại, không phải bản scraper hoàn chỉnh.
