# TICKET-016: A non-feed URL (TLDR homepage) silently yielded 0 entries

**Category:** silent failure
**Module:** `source.yaml`

## Symptom
The TLDR.Tech source consistently contributed zero articles across every run, with no error and no warning logged.

## Root cause
The configured URL pointed at TLDR's HTML homepage, not an actual RSS/Atom feed. `feedparser` parsed it successfully as valid HTML (`bozo=False`, HTTP 200) but found no `<item>`/`<entry>` elements — a case TICKET-014's dead-feed check (HTTP status, `bozo`) doesn't catch, because nothing about the fetch itself failed.

## Fix
Removed TLDR from `source.yaml` (no working feed endpoint found); added a `logger.warning` in `fetch_articles` whenever a source returns 0 entries, so this failure class is visible in logs going forward even when it isn't an HTTP-level error.

## Lesson
"The request succeeded" and "the request returned what I actually wanted" are different checks. A source that is technically reachable but structurally wrong (right domain, wrong content type) won't be caught by status-code or parse-error checks — it needs its own explicit signal, in this case a zero-entries warning.
