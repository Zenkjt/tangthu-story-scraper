from story_scraper.core.engine import StoryEngine
from story_scraper.core.models import Chapter, Story


class State:
    def save(self, story):
        self.story = story


class Epub:
    def create(self, story): pass
    def append(self, story, chapter, content): pass
    def replace(self, story, chapter, content): pass


class Adapter:
    def fetch_chapter(self, chapter): raise AssertionError("jump must not fetch")
    def refresh_tail(self, story): return []


def test_jump_changes_target_without_fetch():
    story = Story("id", "https://example.test", "test", chapters=[
        Chapter(1, "One", "/1"), Chapter(2, "Two", "/2")
    ], target_chapter_number=1)
    engine = StoryEngine(State(), Epub(), Adapter())
    engine.jump_to_chapter(story, 2)
    assert story.target_chapter_number == 2
