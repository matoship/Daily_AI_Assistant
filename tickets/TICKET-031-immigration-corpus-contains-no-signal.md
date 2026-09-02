# TICKET-031: Half the daily corpus carried none of the signal it was added for

**Category:** data quality / product scope
**Module:** `source.yaml`, `profile.yaml`

## Symptom
The immigration half of the digest scored **F1 0.00** on every live evaluation run.
Three separate profile rewrites — tightening the criteria, broadening them, reverting to
production wording — moved it not at all, while the engineering half sat at 0.88–0.92
throughout.

Nothing looked broken. The feeds were live, well-formed, and returning plausible,
on-topic Australian migration articles every single day. `articles_fetched` matched
`articles_scored`. No error, no warning, no failed run.

## Root cause
The corpus contained essentially none of the signal the feeds were added to capture.

The stated interest was SA state nomination (190/491) invitation rounds, ICT occupation
list changes, and Home Affairs processing changes affecting a specific visa pathway.
Searching all 425 corpus rows for pathway terms (`190`, `491`, `state nomination`,
`occupation list`, `subclass`, `points test`, `invitation round`, …) returned **9 matches,
most of them false**:

```
491 -> "Cloudflare Wallets Arrives Late to x402..."
482 -> "JDK 27 and JDK 28: What We Know So Far"
186 -> "Rx.NET 7.0 Reduces Deployment Size..."
190 -> "Hanson lashes out at Australia's treasurer in superannuation fight"
```

Strip the incidental number matches and roughly four genuine hits remain, one of them for
another state, one a duplicate across two Google News redirect URLs.

What the feeds *did* deliver was general migration discourse — party-political statements,
sector lobbying, op-eds. Human labelling of 20 immigration articles rejected 18 of them,
with the same reason written thirteen times: *"Not ICT nor SA related."*

Two compounding causes:

**1. RSS was the wrong instrument for this signal.** Invitation rounds and occupation-list
changes are periodic government publications, not news. `TICKET-014` had already
established that `migration.sa.gov.au` and `immi.homeaffairs.gov.au` have no usable feed,
which is *why* Google News proxies were introduced. The proxy carried the topic but not
the signal.

**2. The authoritative source is itself dormant.** Checking `migration.sa.gov.au` directly
showed no publication since July. A scraper — the planned Phase 4 fix — would have been
built against a source with nothing to scrape.

Cost of the gap: the three immigration queries produced **239 of 425 rows (~7.7 per run,
56% of all triage volume)** at an 8% human-approval rate, versus 100% for MarkTechPost and
46% for InfoQ.

## Fix
- Removed the three Google News immigration queries from `source.yaml`.
- Replaced the immigration topic rather than keeping a section no source can feed.
- Corrected two golden-set labels that contradicted the stated criterion.

## Lesson
**A feed can be healthy, well-formed, on-topic, and still worthless.** Every signal the
pipeline had said this source was fine: it parsed, it returned articles, they were about
migration, the triage scores were plausible, the runs completed. Only human labelling of
actual content revealed that half the daily volume carried nothing wanted. Source quality
is not observable from the pipeline's own health metrics.

**No amount of prompt engineering can extract signal that is not in the input.** Three
profile rewrites and three paid evaluation runs were spent on a category that could not
have worked regardless of wording. The failure was upstream of the LLM entirely — in
source selection — and every layer downstream looked healthy while producing nothing.

**Check whether the source publishes before building to consume it.** The planned scraper
would have been real engineering effort aimed at a site that has published nothing in
months. One manual visit answered a question that architecture could not.

**The eval harness's most valuable output was "stop", not "improve".** It was built to
measure triage quality and tune prompts against a score. What it actually produced was a
decision to delete a feature — a result that no amount of iterating on prompts, models, or
thresholds would ever have surfaced, and that a `runs` table full of green completions
actively concealed.
