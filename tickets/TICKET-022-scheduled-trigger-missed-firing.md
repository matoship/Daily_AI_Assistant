# TICKET-022: Scheduled workflow trigger silently missed a daily firing

**Category:** CI/config
**Module:** `.github/workflows/daily-digest.yaml`

## Symptom
No `daily-digest` run — scheduled or otherwise — appeared for the expected 22:30 UTC firing. `gh run list` showed the last run at `2026-08-05T23:27:31Z` and then nothing, with the check happening ~90 minutes *after* the next scheduled time had already passed. No failed run, no error, no log — just an absence where a run should have been.

## Root cause
Confirmed via GitHub's REST API that nothing was actually misconfigured: the workflow was `active`, sitting on the repo's correct `default_branch` (`Main`), with a correctly-formed cron trigger (`30 22 * * *`). GitHub documents `schedule` (cron) triggers as best-effort — under platform load, a scheduled firing can be delayed by a wide margin or dropped entirely, with no failure event or run record left behind. This is a platform characteristic of Actions' scheduler, not a bug in the workflow file.

## Fix
No code or config fix applied, since there was nothing wrong to fix. Triggered the missed day's run manually via `gh workflow run` + `gh run watch`; it completed successfully in 3m19s, confirming the pipeline itself was healthy and the gap was purely a missed trigger.

## Lesson
A scheduled job that silently fails to fire looks *identical* to a quiet news day — no error, no red X, just nothing happening. That's the CI-scheduling equivalent of TICKET-014/016's silent-zero-entries pattern: absence of an error is not the same as absence of a problem. Cron reliability on a hosted platform can't be assumed; the only way to actually know a scheduled run fired is to check for its evidence (a new `runs` row) after the fact, not to trust that "no failure notification" means "it ran."
