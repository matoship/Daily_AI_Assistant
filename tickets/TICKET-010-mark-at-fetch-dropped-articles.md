# TICKET-010: Mark-at-fetch dedup permanently dropped capped articles

**Category:** design flaw
**Module:** `pipeline.py` (pre-lifecycle version)

## Symptom
A debugging run capped triage at `new_articles[:5]` for cost reasons. On the *next* run, `ingest` returned an empty list — no articles were fetched as "new" at all, even though the feeds had far more than 5 items.

## Root cause
`ingest` marked every fetched article as "seen" in the database at fetch time, before the `[:5]` cap in `run.py` decided which ones actually got triaged. The other ~25 articles were marked seen but never processed — and because "seen" was a permanent boolean, they could never be picked up again, even though the RSS feed would have kept re-serving them.

## Fix
Replaced the boolean "seen" flag with a status lifecycle (`fetched → scored → digested`, see TICKET-011/012/013) where dedup logic treats `fetched`-but-not-yet-`scored` articles as still eligible for retry. This makes "we fetched it" and "we finished processing it" two distinct, separately-tracked facts.

## Lesson
"Have we seen this before?" is often really two different questions — "did we encounter it?" and "did we finish handling it?" — collapsing them into one boolean silently drops work whenever there's a gap between fetching and finishing (a debug cap, a crash, a rate limit). A status lifecycle instead of a boolean makes partial progress recoverable.
