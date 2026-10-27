# TICKET-041: Runs were recorded `completed` and articles marked `digested` before the page was written

**Category:** silent data bug / ordering of state commits
**Module:** `run.py` (`run()` / `main()`), `pyproject.toml`

**Status:** trigger fixed; underlying ordering flaw open (`TODO.md`).

## Symptom
Two local runs (41 on 2026-10-21, 43 on 2026-10-27) logged a successful pipeline, with
synthesis returning 2 and 5 digest items, and then crashed:

```
zoneinfo._common.ZoneInfoNotFoundError: 'No time zone found with key Australia/Adelaide'
```

`seen.db` disagreed with what happened:

```
run 41  digested=2  status='completed'
run 43  digested=5  status='completed'
```

No page was written for either run. There is no `digest_2026-10-21.html`, and the
2026-10-28 sidecar contains only the 3 items from a later run. The 7 articles are in the
terminal `digested` state, so nothing will ever select them again.

## Root cause
Two separate faults.

**Trigger.** `main()` computes the display date with `ZoneInfo("Australia/Adelaide")`.
Windows has no system time-zone database, so `zoneinfo` needs the `tzdata` package, which
had never been a dependency. CI runs on Linux, where the OS supplies the database, so the
failure appeared only on local Windows runs.

**Flaw.** The crash cost data because of commit order:

```
run():  synthesize → mark_digested(url) → finish_run(status="completed") → return
main(): compute date → write sidecar → render page → write index
```

Every state transition is written before any output exists. Any exception in `main()` (a
time-zone lookup, a render bug, a full disk, a permission error) leaves articles
`digested` and the run `completed` with nothing delivered. The `runs` row, which this
project relies on to diagnose incidents, reported success.

## Fix
`tzdata` added as a dependency (`pyproject.toml`, `uv.lock`). Run 45 completed on Windows
and wrote `digest_2026-10-28.html`, its sidecar and an updated index.

The ordering is **not** fixed. It is tracked in `TODO.md`. Recovering the 7 articles is a
separate decision.

## Lesson
**A state transition must not precede the outcome it records.** `digested` should mean
"delivered", and `completed` should mean "the page exists". Recording either one before the
write it describes turns any later failure into silent loss, reported as success. Commit
state after the side effect, or record an intermediate state that a retry can pick up.

**A green CI path does not cover the developer's platform.** The same entry point ran
daily on Linux for weeks. The first full local run on Windows failed, which is the
`TICKET-036` lesson (enter through the same door) applied to the operating system.
