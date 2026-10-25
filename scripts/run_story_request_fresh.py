from __future__ import annotations

from pathlib import Path

from scripts import run_story_request as runner


def _do_not_read_previous_epub(folder_id: str, filename: str, target: Path) -> bool:
    if filename == "0neStory.epub":
        target.unlink(missing_ok=True)
        return False
    return False


runner.download_drive_file = _do_not_read_previous_epub

if __name__ == "__main__":
    raise SystemExit(runner.main())
