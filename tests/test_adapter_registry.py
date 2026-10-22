from story_scraper.core.adapter import AdapterNotApplicable, SiteAdapter
from story_scraper.core.models import Story
from story_scraper.core.registry import AdapterRegistry

class ExactAdapter(SiteAdapter):
    name="exact"; family="platform"; priority=100
    @classmethod
    def matches(cls,url): return "example.com" in url
    def build_index(self,url): return Story("exact",url,self.name)
    def refresh_tail(self,story): return []
    def fetch_chapter(self,chapter): return "",True

class FamilyAdapter(SiteAdapter):
    name="family"; family="static-html"; priority=50
    @classmethod
    def matches(cls,url): return url.startswith("https://")
    def build_index(self,url):
        if "fallback.example" not in url: raise AdapterNotApplicable("not this family")
        return Story("family",url,self.name)
    def refresh_tail(self,story): return []
    def fetch_chapter(self,chapter): return "",True

def test_priority():
    r=AdapterRegistry(); r.register(FamilyAdapter); r.register(ExactAdapter)
    assert r.resolve("https://example.com/story/1")==[ExactAdapter,FamilyAdapter]

def test_fallback():
    r=AdapterRegistry(); r.register(FamilyAdapter)
    assert r.build_index("https://fallback.example/story/1").site=="family"

def test_real_errors_propagate():
    class Broken(FamilyAdapter):
        name="broken"
        def build_index(self,url): raise TimeoutError("network timeout")
    r=AdapterRegistry(); r.register(Broken)
    try: r.build_index("https://fallback.example/story/1")
    except TimeoutError as exc: assert "network timeout" in str(exc)
    else: raise AssertionError("TimeoutError must propagate")
