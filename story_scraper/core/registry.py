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
    """Ordered adapter discovery with family priority and safe fallback."""

    def __init__(self):
        self._adapters: list[Type[SiteAdapter]] = []

    def register(self, adapter: Type[SiteAdapter]) -> None:
        if adapter not in self._adapters:
            self._adapters.append(adapter)

    def candidates(self, url: str) -> list[AdapterCandidate]:
        result=[]
        for adapter in self._adapters:
            try:
                if adapter.probe(url):
                    result.append(AdapterCandidate(adapter,getattr(adapter,"priority",100),
                                                    getattr(adapter,"family","custom")))
            except Exception:
                continue
        return sorted(result,key=lambda x:(-x.priority,x.family,x.adapter.name))

    def resolve(self,url:str)->list[Type[SiteAdapter]]:
        return [x.adapter for x in self.candidates(url)]

    def build_index(self,url:str)->Story:
        candidates=self.candidates(url)
        if not candidates:
            raise AdapterNotApplicable(f"No adapter matches URL: {url}")
        failures=[]
        for item in candidates:
            try:
                return item.adapter().build_index(url)
            except AdapterNotApplicable as exc:
                failures.append(f"{item.adapter.name}: {exc}")
        detail="; ".join(failures)
        raise AdapterNotApplicable(f"No registered adapter accepted URL: {url} ({detail})")
