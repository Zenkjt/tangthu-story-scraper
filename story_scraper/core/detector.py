from __future__ import annotations
from .adapter import SiteAdapter


class SiteDetector:
    def __init__(self, adapters: list[type[SiteAdapter]]):
        self.adapters = adapters

    def detect(self, url: str) -> SiteAdapter:
        for adapter_cls in self.adapters:
            if adapter_cls.matches(url):
                return adapter_cls()
        raise ValueError(f"Unsupported story site: {url}")
