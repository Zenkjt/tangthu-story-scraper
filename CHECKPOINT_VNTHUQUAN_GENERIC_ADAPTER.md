# Checkpoint — vnthuquan / generic static HTML adapter

## Base
- Starting commit: `be812eb`
- Core state model remains unchanged.
- `BasePlatformAdapter` remains the reusable mechanics layer.
- `BaseStaticHTMLAdapter` now provides generic static-HTML transport/parsing helpers.
- vnthuquan-specific code is limited to URL recognition and extraction rules.

## vnthuquan
- Supports `vnthuquan.net` and `thuvien.vnthuquan.net`.
- Accepts story root URLs and numeric `/chuong-N` URLs.
- Builds metadata + chapter manifest from the story page.
- Chapter URLs are normalized and deduplicated.
- Tail refresh inspects the story page and returns only newly discovered chapter numbers.
- Chapter fetch returns HTML content and currently marks public vnthuquan chapters as complete.

## Deliberate scope
The first adapter only targets the numeric `/chuong-N` form. Non-numeric sections such as introductions, named parts, and endings are not yet mapped into the numeric `Chapter.number` model.

## Important
This is the first real adapter test. Do not expand to Wattpad or EPUB work until the vnthuquan index/fetch behavior is verified against a live story.
