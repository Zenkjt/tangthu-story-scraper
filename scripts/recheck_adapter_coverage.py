from __future__ import annotations

import os
from pathlib import Path

from story_scraper.core.adapter import AdapterNotApplicable
from story_scraper.core.registry import default_registry
from story_scraper.core.resolution import AdapterResolutionStore


def main() -> int:
    store = AdapterResolutionStore(
        os.environ.get("ADAPTER_RESOLUTION_STORE", "data/adapter-resolution.jsonl")
    )
    failures = store.failure_list()
    print(f"Active failure domains: {len(failures)}")

    if not failures:
        print("Nothing to recheck.")
        return 0

    registry = default_registry(store)
    checked = success = failed = skipped = 0

    for item in failures:
        if not item.url:
            skipped += 1
            print(f"SKIP  {item.domain}: no URL in resolution history")
            continue

        checked += 1
        print(f"CHECK {item.domain} -> {item.url}")
        try:
            source = registry.recheck_source(item.url)
        except AdapterNotApplicable as exc:
            failed += 1
            print(f"FAIL  {item.domain}: {exc}")
        except Exception as exc:
            failed += 1
            print(f"FAIL  {item.domain}: {type(exc).__name__}: {exc}")
        else:
            success += 1
            print(f"PASS  {item.domain}: {source.adapter.name}")

    print(
        f"Summary: checked={checked}, success={success}, "
        f"still_failed={failed}, skipped={skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
