from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from .adapter import AdapterNotApplicable, SiteAdapter
from .models import Story


@dataclass(frozen=True)
class AdapterCandidate:
    adapter: Type[SiteAdapter]
    priority: int
    family: str


class AdapterRegistry:
    """Resolve URL to matching adapters, then try explicit safe fallbacks."""

    def __init__(self, adapters: list[Type[SiteAdapter]] | None = None):
        self._adapters: list[Type[SiteAdapter]] = []
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: Type[SiteAdapter]) -> None:
        if adapter not in self._adapters:
            self._adapters.append(adapter)

    @staticmethod
    def _probe(adapter: Type[SiteAdapter], url: str) -> bool:
        # Backward-compatible with adapters that only implement matches().
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
        return sorted(
            result,
            key=lambda candidate: (
                -candidate.priority,
                candidate.family,
                candidate.adapter.name,
            ),
        )

    def resolve(self, url: str) -> list[Type[SiteAdapter]]:
        return [candidate.adapter for candidate in self.candidates(url)]

    def resolve_instance(self, url: str) -> SiteAdapter:
        candidates = self.candidates(url)
        if not candidates:
            raise AdapterNotApplicable(f"No adapter matches URL: {url}")
        return candidates[0].adapter()

    def build_index(self, url: str) -> Story:
        candidates = self.candidates(url)
        if not candidates:
            raise AdapterNotApplicable(f"No adapter matches URL: {url}")

        rejected: list[str] = []
        for candidate in candidates:
            adapter = candidate.adapter()
            try:
                return adapter.build_index(url)
            except AdapterNotApplicable as exc:
                rejected.append(f"{candidate.adapter.name}: {exc}")

        detail = "; ".join(rejected) or "all candidates rejected the URL"
        raise AdapterNotApplicable(
            f"No registered adapter accepted URL: {url} ({detail})"
        )


def default_registry() -> AdapterRegistry:
    from ..adapters import WattpadAdapter, VnThuQuanAdapter
    return AdapterRegistry([WattpadAdapter, VnThuQuanAdapter])


def build_story_index(url: str) -> Story:
    return default_registry().build_index(url)
