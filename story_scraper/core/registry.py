from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from .adapter import AdapterNotApplicable, SiteAdapter
from .models import Story
from .resolution import AdapterResolutionStore, classify_resolution_failure, resolution_domain


@dataclass(frozen=True)
class AdapterCandidate:
    adapter: Type[SiteAdapter]
    priority: int
    family: str


@dataclass(frozen=True)
class ResolvedStorySource:
    adapter: SiteAdapter
    story: Story


class AdapterRegistry:
    """Resolve URLs with fast known-failure/known-good coverage checks."""

    def __init__(self, adapters=None, resolution_store: AdapterResolutionStore | None = None):
        self._adapters = []
        self.resolution_store = resolution_store
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter):
        if adapter not in self._adapters:
            self._adapters.append(adapter)

    @staticmethod
    def _probe(adapter, url: str) -> bool:
        probe = getattr(adapter, "probe", None)
        return bool(probe(url)) if probe is not None else bool(adapter.matches(url))

    def candidates(self, url: str) -> list[AdapterCandidate]:
        result = [
            AdapterCandidate(a, getattr(a, "priority", 100), getattr(a, "family", "custom"))
            for a in self._adapters if self._probe(a, url)
        ]
        result.sort(key=lambda c: (-c.priority, c.family, c.adapter.name))
        if self.resolution_store is not None:
            cached = self.resolution_store.latest_success(resolution_domain(url))
            if cached:
                result.sort(key=lambda c: (0 if c.adapter.name == cached else 1,
                                           -c.priority, c.family, c.adapter.name))
        return result

    def resolve(self, url: str):
        return [c.adapter for c in self.candidates(url)]

    def resolve_instance(self, url: str) -> SiteAdapter:
        candidates = self.candidates(url)
        if not candidates:
            raise AdapterNotApplicable(f"No adapter matches URL: {url}")
        return candidates[0].adapter()

    def resolve_source(self, url: str) -> ResolvedStorySource:
        domain = resolution_domain(url)

        # Fast path: a known terminal failure answers immediately.
        if self.resolution_store is not None:
            coverage = self.resolution_store.coverage(domain)
            if coverage.status == "failure":
                raise AdapterNotApplicable(
                    f"Known unsupported domain: {domain} ({coverage.reason})"
                )

        candidates = self.candidates(url)
        if not candidates:
            if self.resolution_store is not None:
                self.resolution_store.record(domain, "__registry__", "failure", "NO_MATCHING_ADAPTER")
            raise AdapterNotApplicable(f"No adapter matches URL: {url}")

        rejected = []
        for candidate in candidates:
            adapter = candidate.adapter()
            try:
                story = adapter.build_index(url)
                if self.resolution_store is not None:
                    self.resolution_store.record(domain, candidate.adapter.name, "success", "RESOLVED")
                return ResolvedStorySource(adapter, story)
            except AdapterNotApplicable as exc:
                if self.resolution_store is not None:
                    self.resolution_store.record(domain, candidate.adapter.name, "failure", "ADAPTER_NOT_APPLICABLE")
                rejected.append(f"{candidate.adapter.name}: {exc}")
            except Exception as exc:
                if self.resolution_store is not None:
                    self.resolution_store.record(domain, candidate.adapter.name, "failure",
                                                  classify_resolution_failure(exc))
                raise

        if self.resolution_store is not None:
            self.resolution_store.record(domain, "__registry__", "failure", "UNSUPPORTED_STRUCTURE")
        raise AdapterNotApplicable(
            f"No registered adapter accepted URL: {url} ({'; '.join(rejected)})"
        )

    def build_index(self, url: str) -> Story:
        return self.resolve_source(url).story


def default_registry(resolution_store=None) -> AdapterRegistry:
    from ..adapters import StaticHTMLFamilyAdapter, VnThuQuanAdapter, WattpadAdapter
    return AdapterRegistry(
        [WattpadAdapter, VnThuQuanAdapter, StaticHTMLFamilyAdapter],
        resolution_store=resolution_store,
    )


def build_story_source(url: str, resolution_store=None) -> ResolvedStorySource:
    return default_registry(resolution_store).resolve_source(url)


def build_story_index(url: str, resolution_store=None) -> Story:
    return build_story_source(url, resolution_store).story
