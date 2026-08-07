# TICKET-023: Same-day reruns silently overwrote the digest; UTC date caused archive gaps

**Category:** design flaw + silent data bug
**Module:** `src/daily_assistant/run.py`

## Symptom
In the aftermath of TICKET-022 (a manual catch-up run plus the delayed scheduled run both firing within the same UTC day), the published `digest_2026-08-07.html` lost content: the manual run produced two rich digest items, and the scheduled run that fired ~90 minutes later silently overwrote the same file with a single, much thinner item. Separately, the archive had no entry at all for what the user considered "yesterday," despite a run having occurred around that time.

## Root cause
Two compounding issues in `main()`:

1. `date = datetime.now(timezone.utc).strftime("%Y-%m-%d")` drove both the digest's filename and its displayed date from UTC. The cron fires at 22:30 UTC — 8:00 AM the *next* day in Adelaide (UTC+9:30) — so a routine morning run is labeled with the UTC date from the day before, from the user's perspective. Combined with TICKET-022's missed firing, no file was ever produced for the UTC date that would have represented the user's "yesterday," while the two same-UTC-day runs (manual catch-up + the recovered schedule) both landed on the same filename instead.
2. `main()` wrote each run's digest to `docs/digest_{date}.html` unconditionally, with no check for whether a digest already existed for that date. A second run on the same calendar day fully overwrote the first rather than adding to it. Since the second run legitimately found far fewer new articles (most were already `scored`/`digested` from the first), the overwrite silently replaced richer content with thinner content — no error, no warning.

While fixing this, also found: `run.py` imported its own module at the top of the file (`from daily_assistant import run, storage`), immediately shadowed by `def run():` defined later in the same file. It only resolved correctly because the `def` happened to come after the import in file order — reordering the file, or ever extracting `main()` elsewhere, would break it with a confusing `TypeError: 'module' object is not callable`. The `storage` half of that import was dead code, shadowed everywhere by the local `with Storage() as storage:` variable.

## Fix
- Digest date now comes from `datetime.now(ZoneInfo("Australia/Adelaide"))` — local time for anything a human reads as "which day," UTC retained for `runs` table timestamps (unambiguous, no reason to localize internal bookkeeping).
- Before writing, `main()` reads a per-day JSON sidecar (`docs/.digest_{date}.json`) if one exists, appends the current run's `DigestItem`s to it, writes the sidecar back, and re-renders the *full* accumulated list to HTML — so a second same-day run adds to the digest instead of replacing it.
- Removed the self-referential `from daily_assistant import run, storage` import.

## Lesson
Timestamps used for *display or file-naming* need to reflect the timezone the reader actually lives in, even when every other timestamp in the system correctly stays in UTC — conflating "technically correct for logging" with "correct for how a human will interpret the output" is what produced the archive gap. Separately, an unconditional overwrite is only safe when the operation is genuinely idempotent per key — here it wasn't, because "new articles this run" isn't a stable, day-independent quantity once dedup state carries over from an earlier run the same day.
