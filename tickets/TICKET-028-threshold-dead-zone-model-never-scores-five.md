# TICKET-028: Selection threshold of 5 is silently identical to a threshold of 6

**Category:** silent design flaw
**Module:** `selection.py`, `triage.py`

## Symptom
Found while analysing the 50-article golden set. The distribution of model-assigned
relevance scores has a hole exactly at the selection threshold:

```
model_relevance: {0:4, 1:4, 2:4, 3:4, 4:13, 6:12, 7:3, 8:3, 9:3}
                                          ↑ no 5s, at all
```

Across 50 articles, triage never once returned a 5 — it jumps from 4 to 6. Human labels
over the same articles used 5 three times, so the value is not intrinsically unusable.

## Root cause
Not diagnosed conclusively; the working explanation is the well-known tendency of LLMs
to avoid the exact midpoint of a rating scale, committing to one side instead. The triage
prompt asks for "a relevance score (0-10)" with no rubric anchoring what a 5 means, which
gives the model nothing to hold onto at the midpoint.

The consequence is concrete regardless of cause: `select_for_synthesis(threshold=5)` and
`threshold=6` select **the identical set of articles**, confirmed by sweeping the threshold
across the golden set. The configured value does not mean what the code implies it means.

## Fix
Not yet applied — documented so the threshold is tuned with knowledge of the dead zone
rather than against an assumed-continuous scale. Candidate directions: anchor the scale in
the prompt with a short rubric (what a 3 / 5 / 8 actually mean), or accept the effective
scale and set the threshold deliberately at a value the model actually emits.

## Lesson
**A configuration value is only meaningful if the thing it filters actually produces values
around it.** A threshold assumes a continuous output distribution; nothing verified that
assumption, and the code read as if 5 and 6 were different choices when they were not.

More generally: this was invisible from the code, from logs, and from reading digests. It
only surfaced from looking at the *distribution* of outputs across many runs — which is an
argument for logging model outputs to a queryable table (`triage_logs`) rather than only to
stdout. The data made a structural property visible that no amount of code review would have.
