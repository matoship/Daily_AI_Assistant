# TICKET-037: Narrowing an except clause before finishing the conversion turned skips into aborts

**Category:** regression / incomplete refactor
**Module:** `run.py`, `adapters.py`, `triage.py`, `synthesize.py`

## Symptom
With the per-article handler narrowed from `except Exception` to `except LLMError`, a single
bad article aborted the entire run. Measured by driving the real adapter, real
`triage_article` and real `run()` with three crafted responses:

| One article's response | Before | After narrowing |
|---|---|---|
| no tool call | skipped | skipped |
| malformed JSON in tool arguments | skipped | **whole run aborted** |
| valid JSON, `relevance=11` | skipped | **whole run aborted** |

## Root cause
The handler was narrowed in the same change that *began* converting provider errors into the
`LLMError` hierarchy, but the conversion was incomplete. Still escaping as foreign types
were `json.JSONDecodeError` from `json.loads(function.arguments)`, a bare `ValueError` for
missing usage, and `pydantic.ValidationError` from `TriageResult(**...)` and
`DigestItem(**...)`. None of these are `LLMError` subclasses, so each one bypassed the
per-article handler and hit the run-level handler instead.

**The width of an `except` clause is a contract with everything it wraps.** Narrowing it is
only safe once everything underneath raises within the new type.

A first attempt to fix the JSON case wrapped `json.loads` but re-raised `ValueError` rather
than `LLMProtocolError` — the guard was added while the escape it was written to prevent
stayed open. That is the pattern recorded in `TICKET-032`.

**Why the tests missed it.** The suite was green throughout. The one test touching malformed
tool arguments asserted `pytest.raises(json.JSONDecodeError)` — it pinned the leak as
correct behaviour.

## Fix
Every raise inside `create()` became `LLMProtocolError`, including the wrapped `json.loads`
and the missing-usage case. Schema violations are converted at the parse boundary in
`triage_article` and `synthesize`, chained with `from exc`. `LLMResponse` gained a
`provider` field so those conversions can report which provider produced the bad output.

## Lesson
**Narrow an exception handler only after everything it wraps has been converted, or in the
same commit.** Otherwise the incomplete half of the refactor becomes load-bearing, and the
symptom appears far from the change.

**A passing test can encode a design flaw.** Asserting that a provider's exception type
escapes the seam documents the leak as intended behaviour, and it will keep doing so through
every later review.

**Schema validation belongs to "the model returned something unusable"** even though it
happens outside the adapter. Splitting that concept by which module noticed forces every
caller to know the internal layering — and to import `pydantic` in order to handle an LLM
failure.
