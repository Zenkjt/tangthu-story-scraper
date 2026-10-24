from types import SimpleNamespace

from story_scraper.core.engine import StoryEngine
from story_scraper.core.models import Chapter, ChapterStatus, Story


class State:
    def save(self, story):
        pass


class Epub:
    def create(self, story):
        pass
    def append(self, story, chapter, content):
        pass
    def replace(self, story, chapter, content):
        pass


class Catalog:
    def __init__(self):
        self.created = 0
        self.updated = 0
    def create(self, story):
        self.created += 1
    def update(self, story):
        self.updated += 1


class Adapter:
    def __init__(self, add_tail=False):
        self.add_tail = add_tail
    def fetch_chapter(self, chapter):
        return "<p>ok</p>", True
    def refresh_tail(self, story):
        if self.add_tail and not any(c.number == 2 for c in story.chapters):
            return [Chapter(2, "Chương 2", "https://example/2")]
        return []


def test_catalog_is_not_rebuilt_for_non_tail_chapter():
    story = Story(
        "s1", "https://example/story", "example",
        chapters=[
            Chapter(1, "Chương 1", "https://example/1",
                    ChapterStatus.PENDING)
        ],
        target_chapter_number=1,
    )
    catalog = Catalog()
    engine = StoryEngine(State(), Epub(), Adapter(False), catalog)
    engine.trigger_next(story)
    assert catalog.updated == 0


def test_catalog_rebuilds_only_when_tail_discovers_new_chapter():
    story = Story(
        "s1", "https://example/story", "example",
        chapters=[
            Chapter(1, "Chương 1", "https://example/1",
                    ChapterStatus.PENDING)
        ],
        target_chapter_number=1,
    )
    catalog = Catalog()
    engine = StoryEngine(State(), Epub(), Adapter(True), catalog)
    engine.trigger_next(story)
    assert catalog.updated == 1
    assert [c.number for c in story.chapters] == [1, 2]
