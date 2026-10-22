# CHECKPOINT — Wattpad Adapter V1

Date: 2026-10-22

## Architecture

Wattpad is implemented as a site-specific adapter under the `api-story` family.

The adapter does NOT attempt to generalize Wattpad behavior to other sites.

## Endpoints confirmed by live probe

### Story manifest

`GET https://www.wattpad.com/api/v3/stories/{story_id}?fields=...`

Confirmed working with story `107024873`.

Returns story metadata and ordered `parts[]`.

### Part metadata

`GET https://www.wattpad.com/api/v3/story_parts/{part_id}`

Confirmed working with part `402782528`.

Used to resolve a direct chapter URL to its parent story via `groupId`.

### Chapter content

`GET https://www.wattpad.com/apiv2/storytext?id={part_id}`

The adapter uses this endpoint to fetch exactly ONE chapter at a time.

This is intentionally isolated inside `WattpadAdapter`; the universal engine does not know this endpoint.

## Chapter identity

- `Chapter.number`: Tàng Thư sequential chapter number.
- `Chapter.external_id`: native Wattpad part ID.

Example:

- number = `1`
- external_id = `402782528`

## Current test story

Story:
`107024873`

Chapter:
`402782528`

Expected manifest size:
45 chapters.

## Important

This version is a live functional test adapter. It does not yet integrate registry/auto-detection or final Story EPUB workflow.

After the live test is green, the next step is to connect this adapter to the existing universal engine and run the actual `0neStory.epub` end-to-end test.
