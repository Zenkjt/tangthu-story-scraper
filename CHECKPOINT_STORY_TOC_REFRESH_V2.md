# CHECKPOINT — Story EPUB + full TOC refresh v2

Date: 2026-10-25

## Chốt

### `0neStory.epub`

Mỗi lần fetch nội dung:

- Không đọc `0neStory.epub` cũ từ Google Drive.
- Tạo EPUB mới hoàn toàn.
- Bìa cố định lấy từ `assets/0neStory.bmp`.
- EPUB chỉ chứa đúng một entry vừa fetch.
- Có navigation EPUB hợp lệ.
- Có cover page thật trong spine.
- Overwrite file `0neStory.epub` trên Drive.

### `0neStoryTOC.epub`

Đây là snapshot của toàn bộ TOC mới nhất.

- Không dùng URL website làm destination trực tiếp của EPUB navigation.
- Mỗi entry có một XHTML nội bộ.
- NCX/EPUB Navigation trỏ tới XHTML nội bộ.
- Rebuild toàn bộ khi TOC thay đổi.

### Full TOC refresh

Khi fetch entry cuối cùng mà Tàng Thư đang biết:

1. Fetch entry hiện tại.
2. Refresh toàn bộ TOC nguồn.
3. Merge snapshot mới bằng stable identity:
   - `external_id` nếu có;
   - URL chuẩn hóa;
   - source chapter number + kind làm fallback.
4. Giữ `status` và `content_hash` của entry cũ.
5. Normalize lại `toc_index`.
6. Giữ target/registered entry theo identity.
7. Nếu TOC thay đổi, rebuild `0neStoryTOC.epub`.
8. Runner upload lại `0neStoryTOC.epub`.

### Content extraction

Với static HTML:

- Ưu tiên `.chapter-c`.
- Sau đó `.chapter-content`, `.reading-content`, `.entry-content`.
- Không fallback toàn trang nếu đã có chapter container.
- Tránh đưa breadcrumb/TOC/navigation vào nội dung EPUB.

TruyenFull được đối chiếu với downloader đang dùng selector `.chapter-c`.

## Repo scope

Patch này chỉ thay đổi:

`Zenkjt/tangthu-story-scraper`

Không có file nào của `Zenkjt/tangthu-opds` trong patch này.
