from story_scraper.core.adapter import AdapterNotApplicable, SiteAdapter
from story_scraper.core.engine import StoryEngine
from story_scraper.core.models import Story
from story_scraper.core.registry import AdapterRegistry, default_registry


class ExactAdapter(SiteAdapter):
    name = "exact"
    family = "platform"
    priority = 100

    @classmethod
    def matches(cls, url):
        return "example.com" in url

    def build_index(self, url):
        return Story("exact", url, self.name)

    def refresh_tail(self, story):
        return []

    def fetch_chapter(self, chapter):
        return "", True


class FamilyAdapter(SiteAdapter):
    name = "family"
    family = "static-html"
    priority = 50

    @classmethod
    def matches(cls, url):
        return url.startswith("https://")

    def build_index(self, url):
        if "fallback.example" not in url:
            raise AdapterNotApplicable("not this static family")
        return Story("family", url, self.name)

    def refresh_tail(self, story):
        return []

    def fetch_chapter(self, chapter):
        return "", True


def test_registry_prioritizes_exact_adapter():
    registry = AdapterRegistry([FamilyAdapter, ExactAdapter])
    assert registry.resolve("https://example.com/story/1") == [
        ExactAdapter,
        FamilyAdapter,
    ]


def test_registry_falls_back_after_explicit_rejection():
    class RejectingExact(ExactAdapter):
        name = "rejecting-exact"

        def build_index(self, url):
            raise AdapterNotApplicable("not a supported story page")

    registry = AdapterRegistry([FamilyAdapter, RejectingExact])
    story = registry.build_index("https://fallback.example/story/1")
    assert story.site == "family"


def test_real_errors_do_not_trigger_fallback():
    class BrokenAdapter(FamilyAdapter):
        name = "broken"

        def build_index(self, url):
            raise TimeoutError("network timeout")

    registry = AdapterRegistry([BrokenAdapter])
    try:
        registry.build_index("https://fallback.example/story/1")
    except TimeoutError as exc:
        assert "network timeout" in str(exc)
    else:
        raise AssertionError("TimeoutError must propagate")


def test_default_registry_recognizes_current_platforms():
    from story_scraper.adapters import WattpadAdapter, VnThuQuanAdapter

    registry = default_registry()
    assert registry.resolve(
        "https://www.wattpad.com/story/107024873-sample"
    )[0] is WattpadAdapter
    assert registry.resolve(
        "https://vnthuquan.net/TacPham/abc-123/"
    )[0] is VnThuQuanAdapter


def test_resolve_instance_returns_implemented_wattpad_adapter():
    from story_scraper.adapters.platforms.wattpad import WattpadAdapter

    adapter = default_registry().resolve_instance(
        "https://www.wattpad.com/story/107024873-sample"
    )
    assert isinstance(adapter, WattpadAdapter)
    assert adapter.__class__.build_index is WattpadAdapter.build_index


def test_resolve_source_keeps_same_adapter_instance_for_engine():
    class TrackingAdapter(ExactAdapter):
        name = "tracking"
        instances = []

        def __init__(self):
            self.build_index_instance = None
            self.__class__.instances.append(self)

        def build_index(self, url):
            self.build_index_instance = self
            return Story("tracking", url, self.name)

    registry = AdapterRegistry([TrackingAdapter])
    source = registry.resolve_source("https://example.com/story/1")

    assert source.adapter is TrackingAdapter.instances[0]
    assert source.adapter.build_index_instance is source.adapter

    class DummyState:
        def save(self, story):
            pass

    class DummyEpub:
        def create(self, story):
            pass

    engine = StoryEngine(DummyState(), DummyEpub(), source.adapter)
    assert engine.adapter is source.adapter
