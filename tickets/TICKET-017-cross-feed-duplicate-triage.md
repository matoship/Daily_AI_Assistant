# TICKET-017: Same article from two feeds triaged twice in one run

**Category:** wasted cost
**Module:** `pipeline.py`

## Symptom
Telemetry from a real run showed 70 articles processed but only 69 unique URLs ever reached `scored`/`digested` status — one article was triaged (and paid for) twice.

## Root cause
Two different Google News query feeds ("Skilled Migration" and "Graduate/485 Visa") independently returned the same underlying story. `ingest`'s dedup check queried the database status per article, and the *first* feed's copy was marked `fetched` — which, per the retry-safe lifecycle rule, is still "eligible for processing." So when the *second* feed served the same URL later in the same run, it read as eligible too, since the database write from the first copy hadn't changed its status to `scored` yet.

## Fix
Added an in-memory `set()` of URLs seen *within the current run*, checked before the database lookup, so a duplicate arriving from a second source in the same run is skipped regardless of what the database currently says.

## Lesson
Cross-run dedup (via the database) and within-run dedup (via an in-memory set) are solving two different problems and both are needed — the database can't be relied on to prevent an item from being processed twice inside a single run's own loop, because its own writes from earlier in that same run may not have "closed the loop" for a status the retry logic treats as still-open.
