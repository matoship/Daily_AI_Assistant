# TICKET-038: A half-applied price correction was locked in by updating the test to match

**Category:** silent data bug / test methodology
**Module:** `telemetry.py`

## Symptom
Every `runs` row and `history.jsonl` entry written after 2026-09-01 understated cost.
Sonnet output tokens were billed at the expired introductory rate for two weeks, then at a
rate that matched neither the old nor the new price sheet.

## Root cause
Introductory pricing carried an expiry recorded only as a trailing comment
(`# introductory rate, expires 2026-09-01`). A comment cannot fire, so nothing happened on
the date; the table simply became wrong and stayed plausible.

The correction was then applied to half the entry — input moved `2.00 → 3.00` while output
stayed at `10.00` instead of `15.00`. The accompanying test was updated to expect
`3.00 / 10.00`, values taken *from the implementation that had just been edited* rather than
from the published price sheet. The suite then actively confirmed the wrong number.

## Fix
Output corrected to `15.00`; the test's expected values taken from published pricing.

## Lesson
**A test's expected values must come from the source of truth, not from the code under
test.** Editing a test until it matches the implementation converts it from a check into a
transcript: it will defend whatever the code happens to do, including the bug.

**A date in a comment is not a mechanism.** Anything with an expiry that changes behaviour
should be data the program can evaluate — a date field it compares against — so the lapse
raises or warns rather than silently mispricing.

**Verify a fix element by element.** The entry has two numbers and only one was corrected;
reading the diff confirmed "pricing updated" while the table stayed wrong.
