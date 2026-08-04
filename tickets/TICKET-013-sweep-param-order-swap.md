# TICKET-013: SQL positional-parameter swap disabled the sweep's time window

**Category:** silent data bug
**Module:** `storage.py`

## Symptom
After adding `updated_at = ?` to the sweep's `SET` clause (so a status change would also bump `updated_at`), the sweep started marking *every* `fetched` article as outdated on every run — including ones fetched moments earlier — defeating the 48-hour grace period entirely.

## Root cause
The SQL statement gained a second `?` placeholder (`SET ... updated_at = ?  WHERE first_seen_at < ?`), but the Python tuple of parameters wasn't reordered to match — `cutoff_iso` landed in the `updated_at` slot and `now` landed in the `WHERE` slot, so the query effectively became "sweep everything, and stamp it with a backdated timestamp."

## Fix
Corrected the parameter order, then switched to named parameters (`:now`, `:cutoff` with a dict) so a future edit can't misalign positions again.

## Lesson
Positional SQL parameters are fragile the moment a statement has more than one placeholder — adding or reordering a clause silently shifts every parameter after it, with no error at any layer. The existing test didn't catch this because both its fixture rows were backdated into the past, so correct and broken code produced the same result; the fix that actually mattered was adding a *fresh, non-backdated* `fetched` row and asserting it survives the sweep — that's the only fixture that dies under the broken parameter order.
