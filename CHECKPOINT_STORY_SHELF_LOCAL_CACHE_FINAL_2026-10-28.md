# TÀNG THƯ — Checkpoint Story Shelf Local Cache

Date: 2026-10-28

## Deployment rule

The GitHub repository is the source of truth for the Apps Script `Code.gs`.
The Google Apps Script project must contain the same `apps-script/Code.gs` as the GitHub repository, plus `StoryCache.gs` in the same Apps Script project.

All replacement files in this package preserve their repository filenames and paths. This package is the single replacement bundle.

## Files in this bundle

### `Zenkjt/tangthu-opds/apps-script/Code.gs`
Complete replacement of the supplied current `Code(6).gs`.
Only the required `doPost()` router addition was made:

```javascript
if (action === 'story_cache') {
  return jsonResponse(storyCache_(body));
}
```

All existing Code.gs content is otherwise preserved.

### `Zenkjt/tangthu-opds/apps-script/StoryCache.gs`
New Apps Script file for shelf-local Story cache.

Supported operations:
- `ensure`
- `read`
- `write`

Storage:
- `StoryState`
- `ZtangthuCache/<story_id>/entry_NNN.json`

No list/scan/TTL/LRU/GC API is exposed.

### `Zenkjt/tangthu-story-scraper/scripts/run_story_request.py`
Complete Story request runner replacement using the shelf-local cache adapter.

### `Zenkjt/tangthu-story-scraper/scripts/story_shelf_cache.py`
Shelf-local cache adapter and Apps Script client.

## Architecture locked

Each registered shelf owns its own `ZtangthuCache`.

```text
<BOOKSHELF>
├── 0neStory.epub
├── 0neStoryTOC.epub
├── StoryState
└── ZtangthuCache/
    ├── <story_id_1>/
    │   ├── entry_001.json
    │   ├── entry_002.json
    │   └── ...
    └── <story_id_2>/
```

The cache is accessed directly by `story_id + entry_id`; it is not scanned.

## Validation performed

- JavaScript syntax checked for `Code.gs`.
- JavaScript syntax checked for `StoryCache.gs`.
- Python syntax checked for both Story Python files.
- ZIP contents verified after packaging.
