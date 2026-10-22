from story_scraper.adapters.platforms.static_html import StaticHTMLFamilyAdapter


class FixtureAdapter(StaticHTMLFamilyAdapter):
    pages = {}
    fetched = []

    def fetch_html(self, url: str) -> str:
        self.fetched.append(url)
        return self.pages[url]


def test_build_index_fetches_only_index_pages():
    FixtureAdapter.fetched = []
    FixtureAdapter.pages = {
        "https://example.test/story/": """
            <html><h1>Book</h1><a href='/story/chuong-1'>Chương 1</a>
            <a href='/story/chuong-2'>Chương 2</a>
            <a href='/story/trang-2/'>2</a></html>
        """,
        "https://example.test/story/trang-2/": """
            <html><a href='/story/chuong-3'>Chương 3</a>
            <a href='/story/trang-1/'>1</a></html>
        """,
    }
    adapter = FixtureAdapter()
    story = adapter.build_index("https://example.test/story/")

    assert [c.number for c in story.chapters] == [1, 2, 3]
    assert set(FixtureAdapter.fetched) == set(FixtureAdapter.pages)
    assert all("chuong-" not in url for url in FixtureAdapter.fetched)


def test_refresh_tail_only_discovers_new_links():
    FixtureAdapter.fetched = []
    FixtureAdapter.pages = {
        "https://example.test/story/": """
            <html><a href='/story/chuong-1'>Chương 1</a>
            <a href='/story/chuong-2'>Chương 2</a>
            <a href='/story/trang-2/'>2</a></html>
        """,
        "https://example.test/story/trang-2/": """
            <html><a href='/story/chuong-3'>Chương 3</a></html>
        """,
    }
    adapter = FixtureAdapter()
    story = adapter.build_index("https://example.test/story/")
    # Simulate a saved manifest that already knows chapter 1 and 2.
    story.chapters = story.chapters[:2]
    updates = adapter.refresh_tail(story)

    assert [c.number for c in updates] == [3]
    assert all("chuong-" not in url for url in FixtureAdapter.fetched)
