# CHECKPOINT — Static HTML Family Adapter V1

Date: 2026-10-22

## Decision

Add a conservative `static-html` family fallback below exact platform adapters.

Resolution order remains:

`URL → exact platform adapter (priority 100) → static-html family adapter (priority 50) → unsupported`

## Scope

The family adapter is intentionally conservative:

- accepts only HTTP/HTTPS URLs at the registry probe stage;
- recognizes chapter links from `chapter/chuong/chương/part/phan/phần + number`;
- requires at least two recognizable chapter links;
- requires a page title;
- extracts author only from common explicit author markers;
- extracts chapter content from article/main/heading parent containers;
- reuses `BaseStaticHTMLAdapter` for HTTP, HTML parsing and image embedding;
- rejects non-story pages with `AdapterNotApplicable`.

It does NOT attempt arbitrary CSS-selector inference or browser automation.

## Important behavior

Exact adapters remain first. Therefore Wattpad and VnThuQuan behavior is unchanged.

A family adapter failure caused by page structure is represented by `AdapterNotApplicable`, allowing registry fallback. Network/parser failures are not silently converted into "unsupported".

## Test

The package includes fixture-style unit tests for:

1. URL matching.
2. Story index extraction.
3. Rejection of ordinary pages.
4. One-chapter fetch.

## Next checkpoint

After these tests are green, add the family adapter to `default_registry()` and run the full registry/application suite.
