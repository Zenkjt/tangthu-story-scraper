# ADAPTER COVERAGE — PHASE 5 (FAILURE-FIRST)

Date: 2026-10-23

## Decision

Resolution is now checked against the global coverage history before doing
network/index work.

Coverage has three states:
- `good`
- `failure`
- `unknown`

## Fast path

If a domain is in the active failure state, resolution returns immediately
with the recorded reason. No adapter/network probing is performed.

If a domain is known good, its successful adapter is prioritized and normal
resolution still verifies it.

Unknown domains use the normal adapter chain:
VnThuQuan -> Wattpad -> StaticHTMLFamily according to registry priority.

## Failure lifecycle

Historical records are append-only.

The active state is determined by the latest record for the domain:
- latest success -> Known Good
- latest failure -> Known Failure

When a new adapter later succeeds for a failed domain, the domain automatically
leaves the active failure list while the old failure history remains.

## UI

The registration UI can expose:
- Known Good List
- Failure List

Failure entries show domain, adapter, reason and timestamp.

## Data ownership

Manifest Store remains unchanged and continues to own per-user/per-story
chapter index metadata. Adapter coverage is global system-level telemetry.

## Invariant

One normal trigger still fetches exactly one chapter.
