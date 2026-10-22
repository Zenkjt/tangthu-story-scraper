from story_scraper.adapters.platforms.static_html import StaticHTMLFamilyAdapter
from story_scraper.core.adapter import AdapterNotApplicable


STORY_HTML = """
<html><head><title>Test Story</title></head>
<body>
<h1>Test Story</h1>
<div class="author">Author A</div>
<a href="/story/chapter-1">Chapter 1</a>
<a href="/story/chapter-2">Chapter 2</a>
<a href="/story/chapter-3">Chapter 3</a>
</body></html>
"""

CHAPTER_HTML = """
<html><body>
<article>
<h1>Chapter 1</h1>
<p>Hello world.</p>
<p>This is chapter content.</p>
</article>
</body></html>
"""


def test_family_matches_any_http_url():
    assert StaticHTMLFamilyAdapter.matches("https://example.org/story")
    assert not StaticHTMLFamilyAdapter.matches("file:///tmp/story.html")


def test_family_builds_conventional_story_index(monkeypatch):
    adapter = StaticHTMLFamilyAdapter()
    monkeypatch.setattr(adapter, "fetch_html", lambda url: STORY_HTML)

    story = adapter.build_index("https://example.org/story")
    assert story.site == "static-html-family"
    assert story.title == "Test Story"
    assert story.author == "Author A"
    assert [c.number for c in story.chapters] == [1, 2, 3]
    assert story.target_chapter_number == 1


def test_family_rejects_non_story_page(monkeypatch):
    adapter = StaticHTMLFamilyAdapter()
    monkeypatch.setattr(
        adapter,
        "fetch_html",
        lambda url: "<html><body><h1>Ordinary page</h1><a href='/x'>Link</a></body></html>",
    )

    try:
        adapter.build_index("https://example.org/")
    except AdapterNotApplicable:
        return
    raise AssertionError("expected AdapterNotApplicable")


def test_family_fetches_one_chapter(monkeypatch):
    adapter = StaticHTMLFamilyAdapter()
    monkeypatch.setattr(adapter, "fetch_html", lambda url: CHAPTER_HTML)

    from story_scraper.core.models import Chapter
    chapter = Chapter(1, "Chapter 1", "https://example.org/story/chapter-1")
    content, complete = adapter.fetch_chapter(chapter)

    assert complete is True
    assert "Hello world." in content.html
