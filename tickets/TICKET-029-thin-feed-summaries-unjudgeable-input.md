# TICKET-029: A third of triage inputs contain too little text to judge

**Category:** data quality
**Module:** `source.py`, `source.yaml`

## Symptom
While labelling the golden set, 18 of 50 articles (36%) were marked
`input_insufficient: true` — meaning no rater, human or model, could reasonably decide
relevance from what the pipeline actually supplies.

Concentrated by source:

| count | source |
|---|---|
| 15 | Google News - Skilled Migration (AU) |
| 2 | Google News - Graduate/485 Visa |
| 1 | InfoQ - Software Development News |

## Root cause
Google News RSS `summary` fields are not summaries. They are a fragment of HTML containing
an anchor tag whose text is the headline, plus the publisher name — the title repeated, with
markup. So for those articles, `triage_article` is scoring on **title alone**, while the
prompt presents it as though a summary were available.

Measured effect on calibration, comparing model score minus human score:

| | mean (model − gold) |
|---|---|
| input sufficient | +0.78 |
| input insufficient | **+1.33** |

The model is *more* generous when it has *less* information — the opposite of the desired
behaviour, which would be to regress toward the middle when evidence is thin.

## Fix
Not yet applied. This is an upstream data problem: no prompt change can recover information
that was never fetched. Options are to fetch the article body for thin entries (resolving
the Google News redirect and extracting content), or to treat "insufficient input" as an
explicit triage outcome rather than forcing a confident score.

## Lesson
**Evaluation reveals data problems, not just model problems.** Every prior tuning idea for
triage assumed the model was the weak link; a third of the corpus turned out to be
unjudgeable at the input stage, which caps achievable quality no matter how good the
prompt or the model is.

The `input_insufficient` flag in the labelling schema is what made this measurable — a
field that separates "the model judged wrongly" from "nothing could have judged this."
Without it, these 18 articles would have been recorded as ordinary model errors and
would have driven prompt tuning that could not possibly have worked.
