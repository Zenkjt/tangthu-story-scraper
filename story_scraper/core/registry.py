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
    matched: bool = False


@dataclass(frozen=True)
class ResolvedStorySource:
    adapter: SiteAdapter
    story: Story


class AdapterRegistry:
    """Resolve URLs by trying adapters in priority order.

    A domain is only recorded as unsupported after every registered adapter
    rejects the URL with AdapterNotApplicable. Real adapter errors stop the
    resolution immediately; they are not silently treated as fallback.
    """

    def __init__(self, adapters=None, resolution_store: AdapterResolutionStore | None = None):
        self._adapters = []
        self.resolution_store = resolution_store
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter):
        if adapter not in self._adapters:
            self._adapters.append(adapter)

    def registered_adapters(self) -> tuple[Type[SiteAdapter], ...]:
        """Return registered adapter classes; no domain list is required."""
        return tuple(self._adapters)

    def registered_adapter_names(self) -> list[str]:
        return [adapter.name for adapter in self._adapters]

    @staticmethod
    def _probe(adapter, url: str) -> bool:
        probe = getattr(adapter, "probe", None)
        return bool(probe(url)) if probe is not None else bool(adapter.matches(url))

    def candidates(self, url: str) -> list[AdapterCandidate]:
        """Return all adapters, matching adapters first, then fallbacks.

        For an unknown domain there may be no match at all. In that case the
        complete adapter chain is still returned, so the first exact adapter
        (VnThuQuan by priority) gets a chance before the generic fallback.
        """
        candidates = [
            AdapterCandidate(
                adapter=a,
                priority=getattr(a, "priority", 100),
                family=getattr(a, "family", "custom"),
                matched=self._probe(a, url),
            )
            for a in self._adapters
        ]

        # For unknown domains, priority is the discovery order. This is
        # intentional: VnThuQuan is an exact/static adapter with higher
        # priority than the generic StaticHTMLFamilyAdapter, so it gets the
        # first chance even when its domain is not known yet.
        candidates.sort(
            key=lambda c: (-c.priority, c.family, c.adapter.name)
        )

        if self.resolution_store is not None:
            cached = self.resolution_store.latest_success(resolution_domain(url))
            if cached:
                candidates.sort(
                    key=lambda c: (
                        0 if c.adapter.name == cached else 1,
                        -c.priority,
                        c.family,
                        c.adapter.name,
                    )
                )

        return candidates

    def resolve(self, url: str):
        return [c.adapter for c in self.candidates(url)]

    def resolve_instance(self, url: str) -> SiteAdapter:
        candidates = self.candidates(url)
        if not candidates:
            raise AdapterNotApplicable(f"No adapter registered for URL: {url}")
        return candidates[0].adapter()

    def resolve_source(self, url: str) -> ResolvedStorySource:
        return self._resolve_source(url, bypass_failure_cache=False)

    def recheck_source(self, url: str) -> ResolvedStorySource:
        """Maintenance-only resolution that bypasses the active failure cache."""
        return self._resolve_source(url, bypass_failure_cache=True)

    def _resolve_source(self, url: str, bypass_failure_cache: bool) -> ResolvedStorySource:
        domain = resolution_domain(url)

        if not bypass_failure_cache and self.resolution_store is not None:
            coverage = self.resolution_store.coverage(domain)
            if coverage.status == "failure":
                raise AdapterNotApplicable(
                    f"Known unsupported domain: {domain} ({coverage.reason})"
                )

        candidates = self.candidates(url)
        rejected = []

        for candidate in candidates:
            adapter = candidate.adapter()
            try:
                story = adapter.build_index(url)
                if self.resolution_store is not None:
                    self.resolution_store.record(
                        domain,
                        candidate.adapter.name,
                        "success",
                        "RESOLVED",
                        url=url,
                    )
                return ResolvedStorySource(adapter, story)
            except AdapterNotApplicable as exc:
                if self.resolution_store is not None:
                    self.resolution_store.record(
                        domain,
                        candidate.adapter.name,
                        "failure",
                        "ADAPTER_NOT_APPLICABLE",
                        url=url,
                    )
                rejected.append(f"{candidate.adapter.name}: {exc}")
            except Exception as exc:
                if self.resolution_store is not None:
                    self.resolution_store.record(
                        domain,
                        candidate.adapter.name,
                        "failure",
                        classify_resolution_failure(exc),
                        url=url,
                    )
                raise

        if self.resolution_store is not None:
            self.resolution_store.record(
                domain,
                "__registry__",
                "failure",
                "UNSUPPORTED_STRUCTURE",
                url=url,
            )
        raise AdapterNotApplicable(
            f"No registered adapter accepted URL: {url} ({'; '.join(rejected)})"
        )

    def build_index(self, url: str) -> Story:
        return self.resolve_source(url).story


def default_registry(resolution_store=None) -> AdapterRegistry:
    from ..adapters import StaticHTMLFamilyAdapter, VnThuQuanAdapter, WattpadAdapter

    return AdapterRegistry(
        [VnThuQuanAdapter, WattpadAdapter, StaticHTMLFamilyAdapter],
        resolution_store=resolution_store,
    )


def build_story_source(url: str, resolution_store=None) -> ResolvedStorySource:
    return default_registry(resolution_store).resolve_source(url)


def build_story_index(url: str, resolution_store=None) -> Story:
    return build_story_source(url, resolution_store).story
