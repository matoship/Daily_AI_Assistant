# TICKET-006: run.py wiring drifted from renamed function signatures

**Category:** integration gap
**Module:** `run.py`

## Symptom
The first end-to-end wiring of `run()` had four separate bugs at once: a missing `client` argument to `triage_article`, `profile.get("sources")` used instead of the dedicated `load_sources()`, and stale keyword arguments (`max_relevance`, `max_articles`) left over from an earlier version of `select_for_synthesis`'s signature.

## Root cause
`run.py` is the one module that calls every other module — and it was the only one with zero test coverage. Each of the pieces it called had been renamed or extended in isolation (with its own unit tests updated), but nothing exercised the call sites in `run.py` itself.

## Fix
Updated each call site to match the current signatures.

## Lesson
"Unit-green" does not imply "integration-green." A composition function that wires several independently-tested modules together is exactly where signature drift hides, because no single module's test suite can catch a caller using it wrong. This is part of why `run()` later needed its own coverage (`test_run.py`) and why logging was added at every stage boundary — to make wiring bugs visible without waiting for a full paid run to surface them.
