# TICKET-030: Truncated triage responses silently dropped articles for weeks

**Category:** silent failure / unused signal
**Module:** `triage.py`, `models.py`, `run.py`, `adapters.py`

## Symptom
The first live run of the eval harness crashed:

```
pydantic_core.ValidationError: 1 validation error for TriageResult
story_hint
  Field required [type=missing, input_value={'relevance': 7, 'categor...pport AI applications."}]
```

The model returned `relevance`, `category` and `reason` — with `reason` ending
mid-sentence — but no `story_hint`.

## Root cause
`triage.py` requested `max_tokens = 300`. Measured across 425 rows of `triage_logs`,
the `reason` field alone averages **128 tokens** and reaches **178**. That budget also
has to cover JSON scaffolding, `category`, `relevance`, and `story_hint`. When a long
`reason` pushes the response into the ceiling, generation stops — and because
`story_hint` is declared **last** in the tool schema, it is the field that disappears.
`TriageResult` requires it, so construction raises.

Two things turned a tight token budget into an invisible, long-lived bug:

**1. The truncation signal existed and was never checked.** `adapters.py` computes
`truncated = response.stop_reason == "max_tokens"` on every response. Nothing in the
codebase reads it. Had `triage_article` checked it before constructing `TriageResult`,
the error would have named the actual cause instead of surfacing as a confusing
missing-field complaint about a schema that looks correct.

**2. Production's defensive error handling hid it.** `run()` wraps each article's triage
in `try/except Exception: logger.exception(...)` so one bad article cannot kill a nightly
run — a deliberate and reasonable choice. The effect was that each truncation logged a
stack trace, silently dropped the article, and let the run report `status="completed"`.

The `runs` telemetry table had recorded the evidence the whole time:

```
run  6:  31 fetched, 30 scored
run 11:  30 fetched, 29 scored
run 17:  29 fetched, 28 scored
run 27:  20 fetched, 19 scored
run 28:  23 fetched, 22 scored
```

Five single-article losses across 31 runs. Nobody had compared those two columns.
(Run 2's larger 36-article gap is the separate incident in TICKET-021.)

## Aggravating factor: the field was never used
`story_hint` appears in exactly three places — its declaration in `models.py`, and its
property and `required` entry in the triage tool schema. It is not written to
`triage_logs`, not read by `selection.py`, not passed to `synthesize`, and never
rendered. Every triage call had been paying output tokens for a field nothing consumed —
and that unused field was both crowding the token budget and, by being last in the
schema, the one that truncation removed.

## Fix
- Removed `story_hint` from `TriageResult` and the triage tool schema.
- Check `LLMResponse.truncated` before parsing, and raise an error naming `max_tokens`.
- Raised `max_tokens` to leave headroom above the observed 178-token `reason` ceiling.
- Log a warning in `run()` when `articles_scored < articles_fetched`.

## Lesson
**The eval harness found a production bug that production was hiding.** `evaluate_live`
has no per-article `try/except`, so it failed loudly on the first occurrence; `run()`'s
defensive handling had been converting the same failure into a silent drop for weeks.
Defensive error handling is correct for an unattended nightly job — but "keep going" must
not mean "say nothing measurable." The `except` block logged, yet nothing ever aggregated
those logs into an alert.

**A computed signal that nothing reads is not observability.** `truncated` was implemented
correctly and would have diagnosed this immediately; because no caller checked it, the
failure surfaced two layers away as a schema error that pointed at the wrong thing. Adding
a field to a response object is only half the work — the other half is a consumer.

**The telemetry already contained the answer.** `articles_fetched` vs `articles_scored`
diverged five separate times and was visible in every run. Recording a metric is not the
same as watching it: a derived invariant worth logging (`scored == fetched`) is worth
asserting out loud when it breaks.

**Check what a field is for before requiring it.** `story_hint` was speculative from the
start and never wired to a consumer, but being `required` in the schema gave it the power
to fail the whole call.
