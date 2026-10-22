from pathlib import Path

from ebooklib import epub
from PIL import Image

from story_scraper.core.models import Chapter, Story
from story_scraper.story_epub import StoryEpubSink


def make_cover(path: Path) -> None:
    Image.new("L", (480, 800), 255).save(path, format="BMP")


def story() -> Story:
    return Story(
        story_id="demo-1",
        source_url="https://example.com/story/demo-1/",
        site="example",
        title="Truyện thử nghiệm",
        author="Tác giả",
        chapters=[
            Chapter(1, "Chương 1", "https://example.com/1"),
            Chapter(2, "Chương 2", "https://example.com/2"),
        ],
        target_chapter_number=1,
    )


def test_create_append_replace(tmp_path):
    cover = tmp_path / "0neStory.bmp"
    output = tmp_path / "0neStory.epub"
    make_cover(cover)

    current = story()
    sink = StoryEpubSink(output, cover)

    sink.create(current)
    sink.append(current, current.chapters[0], "<p>A</p>")

    book = epub.read_epub(str(output))
    assert book.get_item_with_id("chapter-1").content.find(b"<p>A</p>") >= 0

    sink.replace(current, current.chapters[0], "<p>B</p>")
    book = epub.read_epub(str(output))
    chapter = book.get_item_with_id("chapter-1")
    assert b"<p>B</p>" in chapter.content
    assert b"<p>A</p>" not in chapter.content

    sink.append(current, current.chapters[1], "<p>C</p>")
    book = epub.read_epub(str(output))
    assert book.get_item_with_id("chapter-1") is not None
    assert book.get_item_with_id("chapter-2") is not None
    assert [item.file_name for item in book.spine] == [
        "cover.xhtml",
        "story.xhtml",
        "chapter-1.xhtml",
        "chapter-2.xhtml",
    ]


def test_create_uses_480x800_cover(tmp_path):
    cover = tmp_path / "0neStory.bmp"
    output = tmp_path / "0neStory.epub"
    make_cover(cover)

    current = story()
    StoryEpubSink(output, cover).create(current)

    book = epub.read_epub(str(output))
    cover_item = book.get_item_with_id("cover-image")
    with Image.open(__import__("io").BytesIO(cover_item.content)) as image:
        assert image.size == (480, 800)
        assert image.mode == "L"
