# TICKET-004: Regressions reintroduced during a source.py rewrite

**Category:** regression
**Module:** `source.py`

## Symptom
After an edit to add a "missing published date" guard, `fetch_articles` broke with `'tuple' object cannot be interpreted as an integer`, and article summaries went missing.

## Root cause
The rewrite dropped three things that were already correct in the prior version: it checked `entry.get("published")` instead of the actual field `published_parsed`; it lost the `*parsed[:6]` unpacking when constructing `datetime(...)`, passing the whole tuple instead of six positional args; and it dropped the `entry.get("summary", "")` fallback.

## Fix
Restored the correct field name, the unpacking, and the fallback.

## Lesson
A guard added to fix one bug can silently regress adjacent, already-correct code if the surrounding lines are rewritten instead of surgically edited. `test_fetch_feed.py` (built afterward, using a real `feedparser.FeedParserDict`) exists specifically to pin this function's contract so a future edit can't quietly break it again.
