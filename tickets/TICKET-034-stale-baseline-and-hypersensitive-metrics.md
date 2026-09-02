# TICKET-034: A stale baseline and a hypersensitive metric made eval deltas unreadable

**Category:** measurement methodology
**Module:** `eval/golden_set.yaml`, `eval/report.py`

## Symptom
The first three live evaluation runs produced numbers that looked meaningful and were not,
in two separate ways.

Comparing the production profile's live run against the stored offline baseline showed
**F1 0.67 -> 0.75** — apparently a large improvement from a profile that had not changed.
And two runs of the *identical* profile, thirteen minutes apart, differed by **0.04 F1 and
0.07 recall** — apparently meaningful movement from nothing at all.

## Root cause

**1. The frozen baseline went stale because the code changed underneath it.**
`model_relevance` in `golden_set.yaml` is a snapshot of triage output captured when the set
was labelled — rows written 2026-08-12, committed 2026-08-31. TICKET-030's fixes landed
2026-09-02: `story_hint` removed from the tool schema and `max_tokens` raised 300 -> 600.
So offline mode scores the *old* schema and live mode scores the *new* one. Every
live-vs-offline comparison silently mixed a profile change with a schema change, and there
was nothing in the report to indicate it.

**2. The aggregate metric is far more volatile than the model.**
Article-level comparison of two identical-profile runs:

```
same profile, same code:      1 of 50 scores changed   (1 threshold flip)
different profile, same code: 25 of 50 scores changed  (11 threshold flips)
```

Triage is 98% reproducible at `temperature=0`. But that single changed article moved
overall F1 by 0.04 and recall by 0.07 — because the golden set holds only **15
gold-positive articles**, so each one carries 6.7 points of recall. The model is stable;
the metric is twitchy. Reading F1 deltas without knowing that invites attributing noise to
whatever was changed most recently.

## Fix
- Treat the frozen offline scores as history, not as a comparator. The reference point for
  a profile change is the most recent live run under the *same* code, recorded in
  `history.jsonl`.
- Read **flip counts**, not metric deltas, as the primary signal. A change moving fewer
  than ~3 articles is indistinguishable from noise regardless of what F1 reports.
- `history.jsonl` records a profile hash and model id per run so comparisons can be checked
  for what actually differed.

## Lesson
**A frozen baseline silently expires when the code around it changes.** Nothing marks the
moment it stops being comparable — it keeps producing a plausible number, and the number
keeps looking like a measurement of whatever was changed most recently. Any stored
baseline needs to record the code state that produced it, not just the result.

**Establishing the noise floor costs one repeat run and makes every later comparison
legible.** Running the same profile twice was the cheapest and most valuable experiment in
the phase: it converted "F1 moved 0.08, is that real?" into "signal is 25x noise, yes."
Without it, every delta is ambiguous forever.

**Sample size shows up as metric volatility, not as an error message.** Fifteen
gold-positives means each article is worth 6.7 recall points. Nothing in the report says
this; it presents 0.80 with the same confidence it would present a number computed from ten
thousand examples. The aggregate looks authoritative precisely where it is weakest.
