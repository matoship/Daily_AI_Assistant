# TICKET-003: `Topics` vs `topics` casing silently emptied categories

**Category:** silent data bug
**Module:** `profile.py`

## Symptom
`category_options(profile)` returned `[]` against the real `profile.yaml`, even though the file had topics defined.

## Root cause
The function read `profile.get("Topics", {})` (capital T); the real YAML key is lowercase `topics`. `.get()` on a missing key returns the default (`{}`) instead of raising — so the bug produced an empty list, not an error.

## Fix
Corrected the key to `topics`.

## Lesson
The existing unit test passed because its fixture *also* used the invented capital-`Topics` key — the test validated the code against a fabricated shape of the data, not the real one. Any test fixture for a "load external data" function should be checked against an actual sample of that data, not assumed from the code that reads it.
