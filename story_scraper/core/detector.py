from __future__ import annotations
from .adapter import SiteAdapter


class SiteDetector:
    def __init__(self, adapters: list[type[SiteAdapter]]):
        self.adapters = adapters

    def detect(self, url: str) -> SiteAdapter:
        matches = [adapter_cls for adapter_cls in self.adapters if adapter_cls.matches(url)]
        if not matches:
            raise ValueError(f"Unsupported story site: {url}")
        # Adapter order is explicit and deterministic. More-specific adapters
        # should be registered before broad platform-family adapters.
        return matches[0]()
