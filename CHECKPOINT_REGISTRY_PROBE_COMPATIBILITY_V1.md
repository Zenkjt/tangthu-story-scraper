# CHECKPOINT — Registry probe compatibility V1

Date: 2026-10-22

## Test finding

The implemented Wattpad adapter can be imported correctly, but the current
runtime class does not expose `probe()`. The Registry called `adapter.probe()`
unconditionally and therefore failed before it could evaluate `matches()`.

## Fix

Registry probing now uses:

1. `probe(url)` when an adapter provides it.
2. Otherwise `matches(url)`.

This preserves the intended architecture while remaining compatible with
existing adapters that only implement the original `matches()` contract.

## Scope

No adapter behavior was changed. No network logic was changed. Existing
Wattpad/VnThuQuan extraction remains untouched.

After this fix, rerun Adapter Registry Test. If green, the next step is
integration of one resolved adapter instance with StoryEngine.
