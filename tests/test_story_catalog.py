from pathlib import Path

from ebooklib import epub
from PIL import Image

from story_scraper.core.models import Chapter, Story
from story_scraper.story_catalog import StoryCatalogEpubSink


def _make_cover(path: Path) -> None:
    Image.new("RGB", (32, 32), "white").save(path, format="JPEG")


def test_catalog_has_external_links_and_no_chapter_content(tmp_path: Path):
    cover = tmp_path / "cover.jpg"
    output = tmp_path / "0neStoryTOC.epub"
    _make_cover(cover)
    story = Story("story-1", "https://example.test/story", "example.test",
                  "Test Story", "Tester", [
                      Chapter(1, "Chapter 1", "https://example.test/ch1"),
                      Chapter(2, "Chapter 2", "https://example.test/ch2"),
                  ])
    StoryCatalogEpubSink(output, cover).create(story)
    book = epub.read_epub(str(output))
    assert book.get_item_with_id("chapter-1") is None
    assert book.get_item_with_id("chapter-2") is None
    body = book.get_item_with_href("toc.xhtml").get_content().decode("utf-8")
    assert "https://example.test/ch1" in body
    assert "https://example.test/ch2" in body


def test_catalog_update_adds_new_discovered_chapter(tmp_path: Path):
    cover = tmp_path / "cover.jpg"
    output = tmp_path / "0neStoryTOC.epub"
    _make_cover(cover)
    story = Story("story-1", "https://example.test/story", "example.test",
                  "Test Story", "Tester", [Chapter(1, "Chapter 1", "https://example.test/ch1")])
    sink = StoryCatalogEpubSink(output, cover)
    sink.create(story)
    story.chapters.append(Chapter(2, "Chapter 2", "https://example.test/ch2"))
    sink.update(story)
    book = epub.read_epub(str(output))
    assert book.get_item_with_id("chapter-2") is None
    body = book.get_item_with_href("toc.xhtml").get_content().decode("utf-8")
    assert "https://example.test/ch2" in body
