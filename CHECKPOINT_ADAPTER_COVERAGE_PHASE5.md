# ADAPTER COVERAGE / FAILURE-FIRST — PHASE 5

Date: 2026-10-23

## Decision

Before expanding the adapter catalog, resolution becomes **failure-first**.

For a new story registration:

1. Check the global resolution history by domain.
2. If the domain is a known active failure and no new matching adapter exists,
   return the known failure immediately.
3. Do not perform another network/index operation in that case.
4. If a newly added adapter matches the failed domain, automatically re-check.
5. A successful re-check makes the domain `known_good`.
6. Historical failure records are retained.

## Result classes

The coverage report separates domains into:

- `known_good`
- `known_failure`

A domain with no history is simply unknown and is not included until checked.

## Initial adapter coverage

The first coverage pass focuses on:

- VnThuQuanAdapter
- WattpadAdapter
- StaticHTMLFamilyAdapter / generic family coverage

We do not immediately implement new adapters for every failure.

## Failure backlog

`known_failure` becomes the active adapter-development backlog.

When a new adapter is added and successfully resolves a failed domain:

- the domain leaves the active failure list;
- the historical failure remains in the append-only log.

## Fast user experience

The failure-first lookup is intended for the story-registration UI.

The UI can expose:

- Known Good List
- Failure List
- failure reason
- adapter responsible for the latest result

A user registering a known-failed domain can therefore receive an immediate,
meaningful result instead of waiting for a network attempt.

## Safety

A cached failure is not permanent. A matching newly registered adapter causes
a re-check automatically.

`force_recheck=True` is also available for explicit validation/maintenance.

## Ownership

- Manifest = per-user/per-story chapter index.
- Story State = runtime state.
- `0neStory.epub` = content.
- `0neStoryTOC.epub` = navigation/index.
- Adapter Resolution Registry = global coverage/history.

## Invariant

One normal trigger still fetches exactly one chapter.
