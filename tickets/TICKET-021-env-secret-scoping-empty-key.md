# TICKET-021: Environment-scoped secret invisible to the job; no validation caught it

**Category:** CI/config + fail-fast gap
**Module:** `.github/workflows/daily-digest.yaml`, `config.py`

## Symptom
Two separate scheduled/manual runs completed with status `"completed"` and a green checkmark, but produced an empty digest page. Telemetry told the whole story in one row: `articles_fetched=36, articles_scored=0, total_input_tokens=0, status=completed`.

## Root cause
`ANTHROPIC_API_KEY` had been added as a GitHub *environment* secret (scoped to the `github-pages` environment, auto-created when Pages was enabled), not a *repository* secret. Environment secrets are only visible to a job that explicitly declares `environment: <name>` — the digest job doesn't, and shouldn't. `${{ secrets.ANTHROPIC_API_KEY }}` silently evaluated to an empty string rather than erroring. The pipeline then ran with `Anthropic(api_key="")`, every triage call failed authentication instantly, and the per-article `try/except` in `run()` swallowed each failure individually — so the run "completed" with zero real work done.

## Fix
Re-added the key as a **repository** secret (visible to all workflows), removed the environment-scoped duplicate. Also added `Field(..., min_length=1)` to `anthropic_api_key` in `config.py`'s `Settings`, so an empty key fails loudly at startup with a `ValidationError` instead of silently authenticating-and-failing 36 separate times downstream.

## Lesson
Two distinct classes of gap compounded here: a GitHub *configuration* gap (secret scoped to the wrong visibility boundary) and a *code* gap (nothing rejected an empty string as an invalid API key). Fixing only the GitHub side would leave the same failure mode ready to recur under a different misconfiguration; fixing only the code side wouldn't have prevented this specific incident. Diagnosing which layer a "successful but empty" run actually failed in — GitHub's scoping rules vs. the pipeline's own validation — required reading the telemetry row first, then checking secret configuration, in that order.
