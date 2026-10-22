from pathlib import Path

from ebooklib import epub
from PIL import Image

from story_scraper.core.models import Chapter, ChapterAsset, ChapterContent, Story
from story_scraper.story_epub import StoryEpubSink


def make_cover(path: Path) -> None:
    Image.new("L", (480, 800), 255).save(path, format="BMP")


def story() -> Story:
    return Story("demo-1", "https://example.com/story/demo-1/", "example",
                 "Truyện thử nghiệm", "Tác giả",
                 [Chapter(1, "Chương 1", "https://example.com/1"),
                  Chapter(2, "Chương 2", "https://example.com/2")], 1)


def test_create_append_replace(tmp_path):
    cover = tmp_path / "0neStory.bmp"
    output = tmp_path / "0neStory.epub"
    make_cover(cover)
    current = story()
    sink = StoryEpubSink(output, cover)
    sink.create(current)
    sink.append(current, current.chapters[0], "<p>A</p>")
    book = epub.read_epub(str(output))
    assert b"<p>A</p>" in book.get_item_with_id("chapter-1").content
    sink.replace(current, current.chapters[0], "<p>B</p>")
    book = epub.read_epub(str(output))
    chapter = book.get_item_with_id("chapter-1")
    assert b"<p>B</p>" in chapter.content
    assert b"<p>A</p>" not in chapter.content
    sink.append(current, current.chapters[1], "<p>C</p>")
    book = epub.read_epub(str(output))
    assert book.get_item_with_id("chapter-1") is not None
    assert book.get_item_with_id("chapter-2") is not None
    assert [book.get_item_with_id(item[0]).file_name for item in book.spine] == [
        "cover.xhtml", "story.xhtml", "chapter-1.xhtml", "chapter-2.xhtml"
    ]


def test_create_uses_480x800_cover(tmp_path):
    cover = tmp_path / "0neStory.bmp"
    output = tmp_path / "0neStory.epub"
    make_cover(cover)
    StoryEpubSink(output, cover).create(story())
    book = epub.read_epub(str(output))
    cover_item = book.get_item_with_id("cover-image")
    import io
    with Image.open(io.BytesIO(cover_item.content)) as image:
        assert image.size == (480, 800)
        assert image.mode == "L"


def test_chapter_images_are_embedded(tmp_path):
    cover = tmp_path / "0neStory.bmp"
    output = tmp_path / "0neStory.epub"
    make_cover(cover)
    current = story()
    content = ChapterContent(
        '<p>Trang tranh</p><img src="images/chapter-1-001.jpg">',
        [ChapterAsset("images/chapter-1-001.jpg", b"fake-jpeg", "image/jpeg")],
    )
    StoryEpubSink(output, cover).append(current, current.chapters[0], content)
    book = epub.read_epub(str(output))
    assert book.get_item_with_id("asset-images-chapter-1-001-jpg") is not None
    assert b"images/chapter-1-001.jpg" in book.get_item_with_id("chapter-1").content
