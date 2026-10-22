from story_scraper.application import StoryApplication
from story_scraper.core.adapter import SiteAdapter
from story_scraper.core.models import Chapter, Story
from story_scraper.core.registry import AdapterRegistry
from story_scraper.core.state import StoryStateStore


class TrackingAdapter(SiteAdapter):
    name = "tracking"
    family = "test"
    priority = 100
    instances = []

    @classmethod
    def matches(cls, url):
        return "example.test" in url

    def __init__(self):
        self.__class__.instances.append(self)
        self.build_index_calls = 0
        self.fetch_calls = 0

    def build_index(self, url):
        self.build_index_calls += 1
        return Story(
            story_id="story-1",
            source_url=url,
            site=self.name,
            title="Test Story",
            chapters=[
                Chapter(1, "Chapter 1", url + "/1"),
                Chapter(2, "Chapter 2", url + "/2"),
            ],
        )

    def refresh_tail(self, story):
        return []

    def fetch_chapter(self, chapter):
        self.fetch_calls += 1
        return f"<p>{chapter.title}</p>", True


class DummyEpub:
    def __init__(self):
        self.created = []
        self.appended = []

    def create(self, story):
        self.created.append(story.story_id)

    def append(self, story, chapter, content):
        self.appended.append((story.story_id, chapter.number, content))

    def replace(self, story, chapter, content):
        pass


def test_initialize_resolves_source_and_passes_same_adapter_to_engine(tmp_path):
    TrackingAdapter.instances.clear()
    state = StoryStateStore(tmp_path / "state")
    registry = AdapterRegistry([TrackingAdapter])
    app = StoryApplication(state, registry)
    epub = DummyEpub()

    story = app.initialize("https://example.test/story/1", epub)

    assert story.story_id == "story-1"
    assert epub.created == ["story-1"]
    assert len(TrackingAdapter.instances) == 1
    assert TrackingAdapter.instances[0].build_index_calls == 1


def test_trigger_next_resolves_adapter_from_persisted_story(tmp_path):
    TrackingAdapter.instances.clear()
    state = StoryStateStore(tmp_path / "state")
    registry = AdapterRegistry([TrackingAdapter])
    app = StoryApplication(state, registry)
    epub = DummyEpub()

    app.initialize("https://example.test/story/1", epub)
    story = app.trigger_next("story-1", epub)

    assert story.chapters[0].content_hash is not None
    assert story.target_chapter_number == 2
    assert epub.appended == [
        ("story-1", 1, "<p>Chapter 1</p>")
    ]
    assert len(TrackingAdapter.instances) == 2
    assert TrackingAdapter.instances[0].fetch_calls == 0
    assert TrackingAdapter.instances[1].fetch_calls == 1
