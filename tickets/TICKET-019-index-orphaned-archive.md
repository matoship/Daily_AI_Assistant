# TICKET-019: Archive index only ever linked the current day

**Category:** design flaw
**Module:** `run.py` (`main()`)

## Symptom
After two days of digests existed in `docs/`, the index page only linked to the newest one — the previous day's digest file still existed on disk but was no longer reachable from anywhere on the site.

## Root cause
`main()` called `render_index([date])` — hardcoding the current run's single date — instead of building the index from what digest files actually exist on disk.

## Fix
Built the archive list by globbing `docs/digest_*.html`, extracting the date from each filename, and sorting newest-first (which works correctly because filenames use ISO date format, which sorts lexicographically in date order).

## Lesson
An index/listing page should be derived from the actual state of the thing it's indexing (the files on disk), not reconstructed from only the current operation's inputs — otherwise every run silently erases the previous run's discoverability even though its output still exists.
