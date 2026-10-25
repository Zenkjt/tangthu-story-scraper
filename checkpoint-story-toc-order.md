# Checkpoint — Story TOC / Jump theo thứ tự mục lục

Ngày: 2026-10-25

## Quyết định đã chốt

1. `0neStoryTOC.epub` là **mục lục thực tế của nguồn truyện**, không giả định mọi entry đều là chương.
2. Entry đầu tiên có thể là **trang đầu / giới thiệu / lời tựa / mở đầu**, không có số chương.
3. Một truyện có thể **không đánh số chương**; chỉ có tên các entry. Hệ thống vẫn phải đánh số thứ tự trong TOC nội bộ.
4. Số dùng cho `Đi đến` là **số thứ tự trong TOC**, không phải số chương của nguồn.
5. URL đăng ký phải được giữ nguyên và phải tương ứng với một entry trong TOC. Nội dung `0neStory.epub` khi đăng ký phải fetch đúng entry đó.
6. `0neStoryTOC.epub` phải đánh dấu entry tương ứng là `Vị trí đăng ký`.
7. `Next`, `Previous`, và `Đi đến` đều làm việc theo **thứ tự TOC**.
8. GUI:
   - `Chọn chương ...` → `Đi đến`
   - popup: **`Đến số thứ tự trong mục lục:`**
   - hướng dẫn: **`Xem 0neStoryTOC để đối chiếu.`**
9. Các nhãn GUI không nên giả định mọi entry là chương; dùng ngữ nghĩa `mục lục` / `vị trí` khi phù hợp.

## Hệ quả kỹ thuật

- Model cần tách:
  - thứ tự TOC nội bộ;
  - số chương của nguồn (nếu có);
  - loại entry (trang/section/chapter).
- Không được dùng `chapter_number` của nguồn làm khóa jump.
- Không được yêu cầu URL đăng ký phải khớp một chapter có số.
- Không được fallback sai sang chương 1 khi URL đăng ký là trang đầu.
