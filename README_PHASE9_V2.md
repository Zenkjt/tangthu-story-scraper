# Phase 9 v2

## Mục tiêu

Thay thế Phase 9 cũ bằng GUI đúng kiến trúc Tàng Thư.

### Thay thế

- `story_scraper/core/bookshelf.py`
- `story_scraper/core/application_flow.py`
- `story_scraper/core/engine.py`
- `story_scraper/gui.py`

### Không dùng lại

Implementation cũ tạo:

```text
Drive folder/
└── .tangthu/
    ├── state/
    └── manifest/
```

Đó là implementation sai và không được merge.

### Kiến trúc mới

```text
Google Drive receiving folder
├── 0neStory.epub
└── 0neStoryTOC.epub

Story Scraper backend
├── state
├── manifest
└── resolution history
```

`BookshelfBackend` là boundary để nối GUI với registration/delivery backend hiện
có của Tàng Thư.

## Kiểm thử GUI

GUI cần được khởi tạo với một implementation `BookshelfBackend` thật hoặc mock.
Không có default local-folder backend để tránh vô tình tạo kiến trúc lưu state
trong Drive.

## Lưu ý

Code package này là replacement patch cho Phase 9. Không merge `bookshelf.py` /
`application_flow.py` của Phase 9 cũ.
