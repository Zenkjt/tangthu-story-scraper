# Phase 9 v2 — Story Online GUI / Bookshelf Registration

## Trạng thái

Phase 9 được làm lại vì implementation cũ đặt `.tangthu` và state/manifest trong
Google Drive receiving folder. Cách đó **không đúng kiến trúc**.

## Đã khóa

User Drive folder chỉ chứa:

- `0neStory.epub`
- `0neStoryTOC.epub`

Không tạo `.tangthu`, manifest, state hoặc resolution cache trong folder người dùng.

Backend state/manifest/resolution là state nội bộ của Story Scraper.

## GUI

- Nút `Truyện online` mở cửa sổ `Đăng ký đọc online`.
- Header có `?` và `X`, không nằm trong vùng scroll.
- Có bảng thông tin chung.
- Dán link folder → kiểm tra ngay.
- Không có registration → báo:
  `Không có thông tin tủ. Yêu cầu lập tủ sách để nhận sách.`
- Có registration → hiện tên tủ và trạng thái quyền ghi nếu backend biết.
- Không biết quyền ghi thì không chặn; chỉ xử lý lỗi khi upload/write thất bại.
- Link truyện chỉ bật sau khi nhận ra tủ.
- Nút truyện là `Đăng ký`.

## Notification / Bulletin

Bảng tin không tự đóng.

Các sự kiện phải báo:

- scrape thất bại;
- đăng ký truyện thành công;
- tải chapter đầu tiên thành công;
- chuyển/tải chapter thành công;
- lỗi ghi Drive;
- lỗi tải chapter.

Người dùng tự bấm `X` để đóng bảng tin.

## TOC

`0neStoryTOC.epub`:

1. tạo lần đầu khi đăng ký story;
2. không rebuild sau mỗi chapter;
3. chỉ kiểm tra lại chapter index khi trigger xử lý chapter cuối cùng đã biết;
4. nếu tail discovery phát hiện chapter mới thì rebuild TOC;
5. tail discovery không tải nội dung chapter mới trong cùng trigger.

## Một trigger

Một trigger vẫn fetch đúng một chapter.

Previous/jump chỉ thay đổi target; không fetch. GUI hiện tại khi người dùng chọn
chapter để đọc sẽ chuyển target rồi gọi trigger tải chapter đó, phù hợp với
client GUI; core engine vẫn giữ nguyên nguyên tắc một trigger = một chapter.

## Drive integration

Phase 9 v2 không tạo một hệ thống đăng ký tủ thứ hai. `BookshelfBackend` là
interface để nối vào registration/delivery backend Tàng Thư hiện có.

Registration lookup nên dùng cùng semantics với News Crawler:

- folder URL → folder ID;
- kiểm tra registration hiện tại;
- folder ID là identity, folder name chỉ là display.

Không tự suy diễn hoặc lưu registration vào Google Drive folder.


## Upload policy

After initial registration:

- `0neStory.epub` is published after every successful chapter update.
- `0neStoryTOC.epub` is published only when the TOC is first created or when
  tail re-indexing actually changes the chapter index.

Thus normal chapter navigation does not rewrite/re-upload the TOC.
