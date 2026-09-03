# Decision log

Design decisions with the alternatives that were rejected and why. Complements
`ARCHITECTURE.md`'s summary table (what was chosen) and `tickets/` (what broke).

Entries marked **⚖️ Contested** are ones where Kaifeng and the reviewer disagreed. Those
are recorded with the argument on both sides, because the reasoning is the part worth
keeping — and in several of them the reviewer was wrong.

---

## 1. Article dedup: status lifecycle, not a boolean "seen" flag

**Context.** The first design stored `seen_articles(url, first_seen_at)` and skipped any
URL already present.

**Rejected.** A boolean flag. It conflates two different questions — *"did we encounter
this?"* and *"did we finish handling it?"* A debugging cap (`new_articles[:5]`) marked 25
articles seen that were never triaged; they became permanently invisible even though the
RSS window would have re-served them (`TICKET-010`).

**Chosen.** A status column: `fetched → scored → digested`, plus `outdated`. `status`
records an *outcome*, never a derivable fact — age is already answerable from
`first_seen_at`, so storing "old" as a status would give the column two jobs.

**Consequence.** `fetched` is the only limbo state, so it is the only one eligible for
retry — which is what makes a crashed run recoverable.

---

## 2. ⚖️ Contested — the outdated-sweep filter: allowlist, not blocklist

**Reviewer proposed:** `WHERE first_seen_at < :cutoff AND status NOT IN ('digested', 'outdated')`.

**Kaifeng pushed back:** *"why not include scored? shouldn't a digested article be
outdated if it is 48 hours older?"* — two objections at once: that the blocklist would
sweep `scored` rows, and that the semantics of `outdated` were unclear.

**Resolution — Kaifeng was right.** The blocklist would have flipped `scored` articles
(triaged and deliberately rejected — an outcome someone paid a Haiku call for) into
`outdated`, destroying the distinction between "never judged" and "judged and rejected."
Final clause: `WHERE first_seen_at < :cutoff AND status = 'fetched'`.

**Generalisable.** State the condition positively — "sweep only the limbo state" — rather
than enumerating exceptions. An allowlist fails closed when a new status is added later; a
blocklist silently includes it.

---

## 3. Marking articles: after processing, not at fetch

**Rejected.** Mark-at-fetch (at-most-once). Simple, but silently drops work whenever
anything sits between fetching and finishing — a debug cap, a crash, a rate limit.

**Chosen.** Mark-after-processing, with `fetched` remaining eligible for retry
(at-least-once). Safe here specifically *because* RSS feeds are a sliding window that
re-serves recent items — the feed itself is the retry mechanism.

**Trade accepted.** A crash mid-run may re-process an article next time. For a daily
digest, an occasional duplicate is a far cheaper failure than a silent drop.

---

## 4. Selection: per-category top_n, not a flat top-N

**Context.** The first real digest returned 4 items, all `engineering`, on a day with real
migration news available.

**Rejected.** Flat sort-by-relevance then slice. One prolific, high-scoring source can
mathematically occupy every slot.

**Chosen.** Group by category, rank within group, take `top_n_per_category`.

**Note.** LLM relevance ranking does not give balanced coverage for free — fairness across
topics was a deliberate design decision, not an emergent property (`TICKET-008`).

---

## 5. ⚖️ Contested — `"other"` category: hardcoded, not schema-generated

**Reviewer proposed:** deriving the full category enum programmatically.

**Kaifeng pushed back:** *"why can't we just ask Claude to toss the unnecessary category
away? If we really have to add an option, i think hardcode will suffice."*

**Resolution — Kaifeng's call stood.** `category_options(profile) + ["other"]`. The topic
list is data (derived from `profile.yaml`), the escape hatch is code. Adding machinery to
generate one constant string would have been complexity without a payer.

---

## 6. ⚖️ Contested — client layering order: telemetry *outside* the adapter

**Reviewer proposed:** `Anthropic → TrackedClient → AnthropicLLMClient` — reasoning
mechanically ("`TrackedClient` needs a `.messages` attribute, so it must sit next to the
SDK").

**Kaifeng pushed back**, relaying and defending the opposite order: telemetry that reads
`response.usage.input_tokens` is permanently Anthropic-shaped, so underneath the adapter it
could never serve a second provider.

**Resolution — the reviewer was wrong.** Final order:
`Anthropic → AnthropicLLMClient (adapter) → TrackedClient (decorator)`. The tracker now
receives an already-normalised `LLMResponse`, so one implementation serves every provider.
`TrackedMessages` was deleted entirely; `run.py` collapsed from two client variables to one.

**Generalisable.** Put shared, cross-provider behaviour *above* the normalisation
boundary, never below it. The mechanical constraint was a symptom of the wrong choice, not
a reason for it — it disappeared once the tracker was written against `LLMClient`
(`TICKET-024`).

---

## 7. ⚖️ Contested — `estimate_cost` stays in telemetry, not adapters

**Kaifeng proposed** moving it into `adapters.py`, reasoning that pricing is
provider-specific.

**Reviewer argued against**, and this one held: the *formula* (`tokens / 1M × rate`) is the
industry-standard shape, and `PRICING` is keyed by **model name** — a field `LLMResponse`
already normalises. So the table is a registry (data), not provider-specific logic.

**Resolution.** Kept in `telemetry.py`. Moving it below the adapter would have re-created
the exact coupling that decision #6 had just removed.

---

## 8. Storage lives in the repo, committed alongside its output

**Context.** GitHub Actions runners are ephemeral — without persistence, every run would
treat every article as new.

**Rejected.** `actions/cache` (designed for *rebuildable* artifacts; eviction would silently
reset the agent's memory) and an external database (credentials, cost, and operational
weight for one write per day).

**Chosen.** Commit `seen.db` next to `docs/`. One writer, low churn, versioned for free.

**Known cost.** Binary blobs in git history, and the local/CI lineages can conflict — git
cannot merge SQLite, so resolution is "pick one side."

---

## 9. Sources: Google News RSS queries, scraping deferred

**Context.** Two authoritative government feeds returned HTTP 404 and had been silently
contributing zero articles for weeks (`TICKET-014`).

**Rejected (deferred).** Scraping `migration.sa.gov.au`. It's a real subsystem — HTML
parsing that breaks on redesign, change detection, politeness — and deserves its own phase.

**Chosen.** Google News RSS search queries, which are real RSS endpoints over a search and
required no code change to consume.

**Outcome.** Later retired entirely: evaluation showed the migration corpus carried
essentially none of the intended signal (`TICKET-031`). Killing a source based on measured
signal rather than intuition is the decision this project is proudest of.

---

## 10. Golden set: labelled blind, oversampled at the decision boundary

**Rejected.** Labelling with the model's own score visible (anchoring bias — "ground truth"
drifts toward the thing being measured), and uniform random sampling.

**Chosen.** A self-contained HTML labeller that hides the model's score until after each
judgement, sampling ~50% of the budget from the relevance band `{4,5,6}` around the
selection threshold. An `input_insufficient` flag separates *"the model judged wrongly"*
from *"nothing could have judged this."*

**Note.** Errors near the threshold flip precision/recall decisions; errors at 1 or 10
don't. The `input_insufficient` field immediately earned its place — it revealed that 36%
of the corpus was unjudgeable, a data problem no prompt change could fix (`TICKET-029`).

---

## 11. ⚖️ Contested — bulk labelling declined; a better method built instead

**Reviewer recommended** sitting down and hand-labelling articles to build ground truth.

**Kaifeng declined:** *"I have no idea and don't really want to grade the articles."*

**Resolution — the refusal produced a better outcome than compliance would have.** Rather
than grinding through a list, he built the labelling tool in decision #10 — blind, stratified,
with an explicit "unjudgeable" escape. That methodology is more rigorous than the manual
process originally proposed.

**Kept as a reminder** that "I don't want to do it this way" is sometimes a design signal,
not avoidance.

---

## 12. Sanity fixtures kept physically separate from the golden set

**Context.** With no ground truth yet, some way to exercise the eval harness was needed.

**Rejected.** Fabricating golden-set entries. A hand-invented label encodes an assumption
about what a *hard* case looks like — the same failure as a mock that encodes an assumption
about a dependency. A too-easy synthetic set yields a comfortable score that measures nothing.

**Chosen.** `eval/sanity_fixtures.yaml` — three *real* articles chosen because the model's
own output on them was already unambiguous — kept in a **separate file** from
`golden_set.yaml`, so the numbers can never be blended. The header states plainly that
passing proves "triage is stable on easy cases," never "triage is correct."

---

## 13. Evaluation split: offline (free) and live (paid)

**Chosen.** `evaluate_offline` reads frozen scores stored in the golden set; `evaluate_live`
re-runs triage against the current prompt and model. Both return the same shape, so
everything downstream — confusion matrix, metrics, report — is indifferent to the source.

**Why both.** Offline is the fixed baseline and costs nothing, so report formatting can be
iterated on freely. Live is the experiment. Comparing them is the only way to attribute a
change to a prompt edit — and the first live run demonstrated the failure mode by
comparing across a profile change *and* a schema change at once, making the delta
uninterpretable (`TICKET-034`).

---

## 14. Metrics hand-rolled; no scikit-learn or numpy

**Rejected.** `sklearn.metrics`. Tens of megabytes of transitive dependency for three
divisions — and it would hide the one concept the module exists to teach. Dependency weight
also matters directly for the planned container image.

**Chosen.** Confusion matrix and precision/recall/F1 written directly, with the
zero-division cases decided explicitly rather than delegated to a `zero_division=`
parameter. `undefined` (nothing selected) and `0.0` (everything selected was wrong) are
different facts and are reported differently.

---

## 15. Selection threshold is a product decision, not an optimisation

**Context.** A threshold sweep showed F1 flat at 0.67 across thresholds 5, 6 and 7 — the
maths does not pick a winner.

**Choice framing.** At threshold 5, ~43% of digest items are things labelled unwanted; at 7,
precision is 0.89 but half the wanted items are missed. For a digest skimmed over coffee,
precision plausibly matters more — a feed that is half noise trains its reader to stop
reading, at which point recall is irrelevant.

**Also discovered.** The model never emits a relevance of exactly 5, so thresholds 5 and 6
select identical sets — the configured value did not mean what the code implied
(`TICKET-028`).

---

## 16. `truncated` field dropped; truncation *checks* kept

**Context.** Both adapters raise on truncation, which made `LLMResponse.truncated`
provably `False` at every construction site — a field carrying no information
(`TICKET-032`).

**Chosen.** Delete the field; keep and strengthen the guards.

**Caveat learned the hard way.** The first attempt removed the guards along with the field,
restoring `TICKET-030`'s original symptom. The datum and the check are different things:
the datum was dead, the check is what converts a downstream `JSONDecodeError` into
*"the model ran out of tokens."* Check order matters too — the guard must run **before**
`json.loads`, since a truncated response is malformed *because* it was truncated.

---

## 17. ⚖️ Contested — no cron risk on a feature branch

**Reviewer claimed** a required-but-unset `openai_api_key` would break that night's
scheduled run.

**Kaifeng pushed back:** the work was on `phase-3-vllm`, not the default branch.

**Resolution — Kaifeng was right.** GitHub Actions `schedule` triggers fire only on the
repository's default branch, so a workflow on a feature branch never runs on a timer. The
review claim was wrong on the facts.

---

## 18. SDK calls pass every argument explicitly, using provider omit sentinels

**Rejected.** Building a `dict` and splatting it (`**kwargs`). Annotating it
`dict[str, Any]` silences mypy's overload error, but silences it by exemption — a typo'd
`max_token` or a `max_tokens="300"` would sail through at exactly the two places type
checking was added to protect: the paid API boundary and the multi-provider seam.

**Chosen.** Pass every parameter explicitly, using each SDK's own `Omit` sentinel for
optional values. mypy verifies both call sites; the tests assert
`isinstance(request["temperature"], AnthropicOmit)` rather than merely that a key is absent.

---

## 19. One Protocol, one adapter per *wire format*

**Rejected.** A second "universal" protocol layer. `LLMClient` already is that interface;
a second one would mean two contracts to satisfy.

**Chosen.** `LLMClient` (one, stable) with an adapter per wire format — not per vendor.
The Anthropic Messages adapter plus one OpenAI-compatible Chat Completions adapter covers
vLLM, Ollama, LM Studio, llama.cpp, Together, Groq, OpenRouter *and* OpenAI, because they
all implement the same shape.

**Correction in flight.** The first OpenAI adapter was written against the *Responses* API —
OpenAI-proprietary and not the interoperability standard. Chat Completions is the portable
surface.

---

## 20. ⚖️ Contested — concepts before implementation (vLLM)

**Reviewer proposed** proceeding to the local-model implementation.

**Kaifeng pushed back:** *"i'm not sure blindly implement model is the best idea. would it
better i learn some concepts first?"*

**Resolution — Kaifeng's call, and it changed the plan.** The briefing that followed
surfaced something implementation would have hidden: vLLM's advantages (PagedAttention,
continuous batching) are *throughput* optimisations for concurrent load, and this workload
is ~40 sequential requests per day with zero concurrency. vLLM is therefore the right
choice **for the learning goal**, not for the workload — a distinction worth being able to
state out loud rather than implying the throughput was needed.
