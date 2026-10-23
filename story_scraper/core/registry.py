from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from .adapter import AdapterNotApplicable, SiteAdapter
from .models import Story
from .resolution import (
    AdapterResolutionStore,
    KnownResolutionFailure,
    classify_resolution_failure,
    resolution_domain,
)


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
    """Resolve URLs using known-good/known-failure coverage first."""

    def __init__(
        self,
        adapters: list[Type[SiteAdapter]] | None = None,
        resolution_store: AdapterResolutionStore | None = None,
    ):
        self._adapters: list[Type[SiteAdapter]] = []
        self.resolution_store = resolution_store
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: Type[SiteAdapter]) -> None:
        if adapter not in self._adapters:
            self._adapters.append(adapter)

    @staticmethod
    def _probe(adapter: Type[SiteAdapter], url: str) -> bool:
        probe = getattr(adapter, "probe", None)
        if probe is not None:
            return bool(probe(url))
        return bool(adapter.matches(url))

    def candidates(self, url: str) -> list[AdapterCandidate]:
        result: list[AdapterCandidate] = []
        for adapter in self._adapters:
            if self._probe(adapter, url):
                result.append(
                    AdapterCandidate(
                        adapter=adapter,
                        priority=getattr(adapter, "priority", 100),
                        family=getattr(adapter, "family", "custom"),
                    )
                )

        result.sort(
            key=lambda candidate: (
                -candidate.priority,
                candidate.family,
                candidate.adapter.name,
            )
        )

        if self.resolution_store is not None:
            cached = self.resolution_store.latest_success(resolution_domain(url))
            if cached:
                result.sort(
                    key=lambda candidate: (
                        0 if candidate.adapter.name == cached else 1,
                        -candidate.priority,
                        candidate.family,
                        candidate.adapter.name,
                    )
                )

        return result

    def resolve(self, url: str) -> list[Type[SiteAdapter]]:
        return [candidate.adapter for candidate in self.candidates(url)]

    def _check_known_failure(
        self,
        url: str,
        candidates: list[AdapterCandidate],
        force_recheck: bool,
    ) -> None:
        if self.resolution_store is None or force_recheck:
            return

        domain = resolution_domain(url)
        failure = self.resolution_store.latest_failure(domain)
        if failure is None:
            return

        failed_adapters = self.resolution_store.failed_adapters_since_latest_success(
            domain
        )
        candidate_names = {candidate.adapter.name for candidate in candidates}

        # A newly added adapter that matches this domain is a reason to retry.
        if candidate_names - failed_adapters:
            return

        raise KnownResolutionFailure(
            f"Known failure for {domain}: {failure.reason} "
            f"(adapter={failure.adapter})"
        )

    def resolve_instance(self, url: str) -> SiteAdapter:
        candidates = self.candidates(url)
        if not candidates:
            raise AdapterNotApplicable(f"No adapter matches URL: {url}")
        return candidates[0].adapter()

    def resolve_source(
        self,
        url: str,
        *,
        force_recheck: bool = False,
    ) -> ResolvedStorySource:
        candidates = self.candidates(url)
        domain = resolution_domain(url)

        # Check the active failure list before doing any network/index work.
        # An empty candidate list is also a known failure unless force_recheck
        # is requested.
        self._check_known_failure(url, candidates, force_recheck)

        if not candidates:
            if self.resolution_store is not None:
                self.resolution_store.record(
                    domain,
                    "__registry__",
                    "failure",
                    "NO_MATCHING_ADAPTER",
                )
            raise AdapterNotApplicable(f"No adapter matches URL: {url}")

        rejected: list[str] = []
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
                    )
                return ResolvedStorySource(adapter=adapter, story=story)
            except AdapterNotApplicable as exc:
                if self.resolution_store is not None:
                    self.resolution_store.record(
                        domain,
                        candidate.adapter.name,
                        "failure",
                        "ADAPTER_NOT_APPLICABLE",
                    )
                rejected.append(f"{candidate.adapter.name}: {exc}")
            except Exception as exc:
                reason = classify_resolution_failure(exc)
                if self.resolution_store is not None:
                    self.resolution_store.record(
                        domain,
                        candidate.adapter.name,
                        "failure",
                        reason,
                    )
                raise

        detail = "; ".join(rejected) or "all candidates rejected the URL"
        raise AdapterNotApplicable(
            f"No registered adapter accepted URL: {url} ({detail})"
        )

    def build_index(
        self,
        url: str,
        *,
        force_recheck: bool = False,
    ) -> Story:
        return self.resolve_source(url, force_recheck=force_recheck).story


def default_registry(
    resolution_store: AdapterResolutionStore | None = None,
) -> AdapterRegistry:
    from ..adapters import (
        StaticHTMLFamilyAdapter,
        VnThuQuanAdapter,
        WattpadAdapter,
    )

    return AdapterRegistry(
        [WattpadAdapter, VnThuQuanAdapter, StaticHTMLFamilyAdapter],
        resolution_store=resolution_store,
    )


def build_story_source(
    url: str,
    resolution_store: AdapterResolutionStore | None = None,
    *,
    force_recheck: bool = False,
) -> ResolvedStorySource:
    return default_registry(resolution_store).resolve_source(
        url,
        force_recheck=force_recheck,
    )


def build_story_index(
    url: str,
    resolution_store: AdapterResolutionStore | None = None,
    *,
    force_recheck: bool = False,
) -> Story:
    return build_story_source(
        url,
        resolution_store,
        force_recheck=force_recheck,
    ).story
