# TICKET-005: Feed mock used plain dict, not `FeedParserDict`

**Category:** mock drift
**Module:** `tests/test_fetch_feed.py`

## Symptom
`fetch_articles` failed against the test's mock feed entries with an `AttributeError` on `.link`.

## Root cause
The test built mock entries as plain Python dicts. Real `feedparser` entries are `FeedParserDict` objects, which support *both* attribute access (`entry.link`) and dict-style `.get()` — the production code used attribute access, which a plain dict doesn't support.

## Fix
Rebuilt the mock entries using `feedparser.FeedParserDict(...)` so the mock has the same interface as the real dependency.

## Lesson
Same root cause as TICKET-001 and TICKET-002: a mock is only useful if it matches the real dependency's *actual* interface, not a simplified guess at it. When mocking a third-party object, prefer constructing it via the library's own type if one exists, rather than a bare dict/object that merely looks similar.
