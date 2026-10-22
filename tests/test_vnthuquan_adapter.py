from story_scraper.adapters.platforms.vnthuquan import VnThuQuanAdapter

STORY_URL = "https://vnthuquan.net/TacPham/ba-nguoi-ban-16110/"


def test_matches_vnthuquan():
    assert VnThuQuanAdapter.matches(STORY_URL)
    assert VnThuQuanAdapter.matches(STORY_URL + "chuong-12")
    assert not VnThuQuanAdapter.matches("https://example.com/TacPham/foo-1/")


def test_chapter_links_are_normalized_and_deduped():
    adapter = VnThuQuanAdapter()
    html = """<html><body>
      <a href="/TacPham/ba-nguoi-ban-16110/chuong-2">Chương 2</a>
      <a href="/TacPham/ba-nguoi-ban-16110/chuong-1">Chương 1</a>
      <a href="/TacPham/ba-nguoi-ban-16110/chuong-2">duplicate</a>
      <a href="/TacPham/other-9/chuong-1">other story</a>
    </body></html>"""
    assert adapter._chapter_links(html, STORY_URL) == [
        (1, "Chương 1", "https://vnthuquan.net/TacPham/ba-nguoi-ban-16110/chuong-1"),
        (2, "Chương 2", "https://vnthuquan.net/TacPham/ba-nguoi-ban-16110/chuong-2"),
    ]


def test_build_index_uses_story_page_and_chapter_manifest():
    adapter = VnThuQuanAdapter()
    adapter.fetch_html = lambda url: """<html><body>
      <h2>Duyên Anh</h2><h1>Đồi Fanta</h1>
      <a href="/TacPham/doi-fanta-288/chuong-1">Chương 1</a>
      <a href="/TacPham/doi-fanta-288/chuong-2">Chương 2</a>
    </body></html>"""
    story = adapter.build_index("https://vnthuquan.net/TacPham/doi-fanta-288/")
    assert story.title == "Đồi Fanta"
    assert story.author == "Duyên Anh"
    assert [c.number for c in story.chapters] == [1, 2]
    assert story.target_chapter_number == 1


def test_chapter_images_are_extracted_and_rewritten():
    adapter = VnThuQuanAdapter()
    adapter.fetch_asset = lambda url: (b"jpeg-data", "image/jpeg")
    html = """<html><body><h1>Chương 1</h1>
      <div><img data-src="/images/a.jpg"><img src="https://example.com/b.png"></div>
    </body></html>"""
    title, content, complete = adapter.parse_chapter_page(html, STORY_URL + "chuong-1", 1)
    assert title == "Chương 1"
    assert complete is True
    assert len(content.assets) == 2
    assert 'src="images/chapter-1-001.jpg"' in content.html
    assert 'src="images/chapter-1-002.jpg"' in content.html
