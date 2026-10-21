# Tàng thư Story Scraper Core

Lõi đầu tiên, bóc tách theo kiến trúc FanFicFare nhưng không phụ thuộc FanFicFare.

## Đã có

- Site Detector
- Site Adapter interface
- Story / Chapter state
- JSON state store
- one-trigger-one-chapter engine
- OPEN chapter → fetch lại + replace khi nội dung thay đổi
- tail re-index khi hết chapter đã biết
- EpubSink interface để gắn downloader/EPUB builder hiện có
- Wattpad adapter skeleton

## Chưa làm trong checkpoint này

- selector/API cụ thể của Wattpad
- EPUB implementation cụ thể
- HTTP/API server
- CrossPoint plugin
- Web UI

Đây là chủ ý: core engine phải độc lập với website, UI và EPUB implementation.
