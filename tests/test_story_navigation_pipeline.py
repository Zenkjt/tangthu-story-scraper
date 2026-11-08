from pathlib import Path

import pytest

from scripts.run_story_request import execute_navigation, resolve_navigation_target
from story_scraper.core.models import Chapter, Story


def make_story(current=5, target=6):
    return Story(
        "story-id",
        "https://example.test/story",
        "example",
        chapters=[
            Chapter(number=i, title=f"Chapter {i}", url=f"https://example.test/{i}")
            for i in range(1, 8)
        ],
        current_toc_index=current,
        target_toc_index=target,
    )


@pytest.mark.parametrize(
    ("action", "requested", "expected"),
    [
        ("next", None, 6),
        ("previous", None, 4),
        ("jump", 2, 2),
    ],
)
def test_navigation_resolves_canonical_toc_index(action, requested, expected):
    assert resolve_navigation_target(make_story(), action, requested) == expected


def test_previous_uses_current_entry_not_prefetched_target():
    # After Next, current=5 while target=6. Previous must fetch 4, not 5.
    story = make_story(current=5, target=6)
    assert resolve_navigation_target(story, "previous") == 4


def test_previous_rejects_first_entry():
    story = make_story(current=1, target=2)
    with pytest.raises(ValueError, match="vị trí đầu tiên"):
        resolve_navigation_target(story, "previous")


def test_previous_requires_current_entry():
    story = make_story(current=None, target=1)
    with pytest.raises(ValueError, match="Chưa có vị trí hiện tại"):
        resolve_navigation_target(story, "previous")


@pytest.mark.parametrize("bad_index", [0, 8, "not-a-number", None])
def test_jump_rejects_invalid_toc_index(bad_index):
    with pytest.raises(ValueError):
        resolve_navigation_target(make_story(), "jump", bad_index)


def test_execute_navigation_runs_common_fetch_publish_and_state_pipeline(
    tmp_path, monkeypatch
):
    import scripts.run_story_request as runner

    story = make_story(current=5, target=6)
    events = []

    class FakeApp:
        def set_target(self, user_id, story_id, toc_index):
            events.append(("set_target", toc_index))
            story.target_toc_index = toc_index

        def trigger_next(self, user_id, story_id, epub, catalog=None):
            events.append(("fetch", story.target_toc_index))
            story.current_toc_index = story.target_toc_index
            story.target_toc_index = story.current_toc_index + 1
            Path(epub.sink.output_path).write_bytes(b"epub")
            return story

    monkeypatch.setattr(
        runner, "write_story_state",
        lambda folder_id, result: events.append(("state", result.current_toc_index)),
    )
    monkeypatch.setattr(
        runner, "upload_drive",
        lambda folder_id, filename, payload: events.append(("upload", filename)),
    )
    monkeypatch.setattr(
        runner, "update_operation",
        lambda request, status, message, result: events.append(("operation", status)),
    )
    monkeypatch.setattr(
        runner, "update_source_coverage",
        lambda: events.append(("coverage",)),
    )

    story_path = tmp_path / "0neStory.epub"
    catalog_path = tmp_path / "0neStoryTOC.epub"
    catalog_path.write_bytes(b"catalog")
    request = {"action": "previous"}

    result = execute_navigation(
        FakeApp(),
        request,
        story,
        user_id="user",
        story_id="story-id",
        folder_id="folder",
        story_path=story_path,
        catalog_path=catalog_path,
        catalog=object(),
    )

    assert result.current_toc_index == 4
    assert events == [
        ("set_target", 4),
        ("fetch", 4),
        ("state", 4),
        ("upload", "0neStory.epub"),
        ("operation", "completed"),
        ("coverage",),
    ]
