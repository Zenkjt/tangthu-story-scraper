from __future__ import annotations

from .core.engine import StoryEngine


class StoryApplication:
    def __init__(self, source, manifest, state, epub, catalog=None):
        self.source = source
        self.manifest = manifest
        self.state = state
        self.epub = epub
        self.catalog = catalog

    def initialize(
        self,
        user_id: str,
        url: str,
        start_toc_index: int | None = None,
        start_chapter_number: int | None = None,
    ):
        story = self.source.resolve(url)
        story = story if story is not None else self.source.adapter.build_index(url)
        story.normalize_toc()

        if start_toc_index is not None:
            story.target_toc_index = start_toc_index
        elif start_chapter_number is not None:
            for entry in story.chapters:
                if entry.number == start_chapter_number:
                    story.target_toc_index = entry.toc_index
                    break

        self.manifest.save(user_id, story)

        engine = StoryEngine(
            adapter=self.source.adapter,
            state=self.state,
            epub=self.epub,
            catalog=self.catalog,
        )

        story = engine.initialize(story)

        if self.source.adapter.fetch_initial_target_on_register(story):
            story = engine.trigger_next(story)

        self.manifest.save(user_id, story)
        return story
