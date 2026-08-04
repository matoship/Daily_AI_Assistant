# TICKET-014: Dead government RSS feeds silently returned zero articles

**Category:** silent failure
**Module:** `source.py`, `source.yaml`

## Symptom
The migration/immigration side of the digest never produced a single article across multiple real runs, with no error anywhere in the pipeline.

## Root cause
Two of the five source URLs (`migration.sa.gov.au/rss`, `immi.homeaffairs.gov.au/rss`) returned HTTP 404. `feedparser.parse()` does not raise on an HTTP error — it returns a feed object with zero entries and no exception, so the failure was completely invisible to the pipeline.

## Fix
Probed all source URLs directly (script hitting each with a real HTTP request), confirmed the two 404s, and replaced them with tested Google News RSS search-query feeds covering the same beats (skilled migration, 485/graduate visa, SA-specific coverage) since no working RSS endpoint exists for the original government sources.

## Lesson
A library choosing to fail silently (return an empty result instead of raising) becomes the caller's problem the moment nobody checks for it — `feedparser`'s "no entries" and "HTTP error" look identical unless you inspect `feed.status` / `feed.bozo` explicitly. Any external HTTP-backed dependency deserves an explicit check for "did this actually work," not just "did it return something."
