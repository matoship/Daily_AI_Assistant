# Decision log

Design decisions, the alternatives considered, and why they were rejected. Complements
`ARCHITECTURE.md` (what the system is) and `tickets/` (what broke).

A decision earns an entry here when a real alternative existed. Recording only the winner
would make this a changelog; the rejected option and its reasoning are the useful part.

---

## 1. Article dedup: status lifecycle, not a boolean "seen" flag

**Context.** Deduplication initially stored `seen_articles(url, first_seen_at)` and skipped
any URL already present.

**Alternative considered:** a boolean seen/not-seen flag. Rejected because it conflates two
different questions — *"did we encounter this?"* and *"did we finish handling it?"* A
debugging cap (`new_articles[:5]`) marked 25 articles seen that were never triaged; they
became permanently invisible even though the RSS window would have re-served them
(`TICKET-010`).

**Decision.** A status column: `fetched → scored → digested`, plus `outdated`. `status`
records an *outcome*, never a derivable fact — age is already answerable from
`first_seen_at`, so storing "old" as a status would give the column two jobs.

**Consequence.** `fetched` is the only limbo state, so it is the only one eligible for
retry — which is what makes a crashed run recoverable.

---

## 2. Outdated-sweep filter: allowlist, not blocklist

**Alternative considered:** `WHERE first_seen_at < :cutoff AND status NOT IN ('digested', 'outdated')`.
Rejected because it would also sweep `scored` articles — ones that were triaged and
deliberately rejected, an outcome a paid Haiku call produced. Flipping those to `outdated`
destroys the distinction between "never judged" and "judged and rejected."

**Decision.** `WHERE first_seen_at < :cutoff AND status = 'fetched'`.

**Rationale.** State the condition positively — sweep only the limbo state — rather than
enumerating exceptions. An allowlist fails closed when a new status is added later; a
blocklist silently includes it.

---

## 3. Marking articles: after processing, not at fetch

**Alternative considered:** mark-at-fetch (at-most-once). Rejected because it silently
drops work whenever anything sits between fetching and finishing — a debug cap, a crash, a
rate limit.

**Decision.** Mark-after-processing, with `fetched` remaining eligible for retry
(at-least-once). This is safe here specifically because RSS feeds are a sliding window that
re-serves recent items: the feed itself is the retry mechanism.

**Trade accepted.** A crash mid-run may re-process an article next time. For a daily
digest, an occasional duplicate is a far cheaper failure than a silent drop.

---

## 4. Selection: per-category top_n, not a flat top-N

**Context.** The first real digest returned four items, all `engineering`, on a day when
relevant migration news was available.

**Alternative considered:** flat sort-by-relevance then slice. Rejected because one
prolific, high-scoring source can mathematically occupy every slot.

**Decision.** Group by category, rank within group, take `top_n_per_category`.

**Rationale.** LLM relevance ranking does not produce balanced coverage for free. Fairness
across topics is a design decision, not an emergent property (`TICKET-008`).

---

## 5. The `"other"` category is hardcoded, not schema-generated

**Alternative considered:** deriving the full category enum programmatically, including the
fallback. Rejected as machinery without a payer — generating one constant string added
complexity for no benefit.

**Decision.** `category_options(profile) + ["other"]`. The topic list is data (derived from
`profile.yaml`); the escape hatch is code.

---

## 6. Client layering: telemetry sits above the adapter

**Alternative considered:** placing telemetry below the adapter
(`Anthropic → TrackedClient → AnthropicLLMClient`). Rejected because it would couple shared
telemetry to Anthropic's response format: a tracker reading `response.usage.input_tokens`
is permanently provider-shaped and could never serve a second backend without per-provider
branching.

**Decision.** `Anthropic → AnthropicLLMClient (adapter) → TrackedClient (decorator)`. The
tracker receives an already-normalised `LLMResponse`, so one implementation serves every
provider. `TrackedMessages` was deleted; `run.py` collapsed from two client variables to one.

**Rationale.** Put shared, cross-provider behaviour *above* the normalisation boundary,
never below it. The apparent mechanical constraint — that a tracker "needs" a `.messages`
attribute — was a symptom of the wrong layering, not a reason for it; it disappeared once
the tracker was written against `LLMClient` (`TICKET-024`).

---

## 7. Cost estimation stays in telemetry, not in adapters

**Alternative considered:** moving `estimate_cost` into `adapters.py`, on the grounds that
pricing is provider-specific. Rejected because it separates the wrong thing: the *formula*
(`tokens / 1M × rate`) is the industry-standard shape, and `PRICING` is keyed by **model
name** — a field `LLMResponse` already normalises. The table is a registry (data), not
provider-specific logic.

**Decision.** Kept in `telemetry.py`. Moving it below the adapter would re-create exactly
the coupling decision 6 removed.

---

## 8. Storage is committed to the repo alongside its output

**Context.** GitHub Actions runners are ephemeral; without persistence every run would
treat every article as new.

**Alternatives considered:** `actions/cache`, rejected because it is designed for
*rebuildable* artifacts and eviction would silently reset the agent's memory — the wrong
durability class for state that matters. An external database, rejected as credentials,
cost, and operational weight for one write per day.

**Decision.** Commit `seen.db` next to `docs/`. One writer, low churn, versioned for free.

**Known cost.** Binary blobs accumulate in git history, and the local and CI lineages can
conflict — git cannot merge SQLite, so resolution is "pick one side."

---

## 9. Sources: Google News RSS queries; scraping deferred, then retired

**Context.** Two authoritative government feeds returned HTTP 404 and had been silently
contributing zero articles for weeks (`TICKET-014`).

**Alternative considered (deferred):** scraping `migration.sa.gov.au`. Rejected for now as
a subsystem in its own right — HTML parsing that breaks on redesign, change detection,
politeness — deserving its own phase rather than being bolted on.

**Decision.** Google News RSS search queries: real RSS endpoints over a search, consumable
with no code change.

**Outcome.** Later retired entirely. Evaluation showed the migration corpus carried
essentially none of the intended signal (`TICKET-031`). Killing a source on measured signal
rather than intuition is the decision this project is proudest of.

---

## 10. Golden set: labelled blind, oversampled at the decision boundary

**Alternatives considered:** labelling with the model's score visible, rejected because of
anchoring bias — "ground truth" drifts toward the thing being measured. Uniform random
sampling, rejected because errors near the threshold flip precision/recall decisions while
errors at 1 or 10 do not.

**Decision.** A self-contained HTML labeller that hides the model's score until after each
judgement, drawing ~50% of the sample from the relevance band `{4,5,6}` around the
selection threshold. An `input_insufficient` flag separates *"the model judged wrongly"*
from *"nothing could have judged this."*

**Outcome.** The `input_insufficient` flag immediately earned its place: 36% of the corpus
was unjudgeable, a data problem no prompt change could fix (`TICKET-029`).

---

## 11. Sanity fixtures kept physically separate from the golden set

**Context.** Before ground truth existed, the eval harness still needed exercising.

**Alternative considered:** fabricating golden-set entries. Rejected because a hand-invented
label encodes an assumption about what a *hard* case looks like — the same failure mode as
a mock that encodes an assumption about a dependency. A too-easy synthetic set yields a
comfortable score that measures nothing, and the gap only surfaces later, indistinguishably
from a broken harness.

**Decision.** `eval/sanity_fixtures.yaml` holds three *real* articles chosen because the
model's own output on them was already unambiguous, in a **separate file** from
`golden_set.yaml` so the numbers can never be blended. The header states plainly that
passing proves "triage is stable on easy cases," never "triage is correct."

---

## 12. Evaluation split into offline (free) and live (paid)

**Decision.** `evaluate_offline` reads frozen scores stored in the golden set;
`evaluate_live` re-runs triage against the current prompt and model. Both return the same
shape, so the confusion matrix, metrics and report are indifferent to the source.

**Rationale.** Offline is a fixed baseline costing nothing, so report code can be iterated
freely. Live is the experiment. Comparing them is the only way to attribute a change to a
prompt edit — a point demonstrated by the first live run, which varied a profile change and
a schema change simultaneously and produced an uninterpretable delta (`TICKET-034`).

---

## 13. Metrics hand-rolled; no scikit-learn or numpy

**Alternative considered:** `sklearn.metrics`. Rejected on three grounds — tens of
megabytes of transitive dependency for three divisions; dependency weight matters directly
for the planned container image; and it would hide the one concept the module exists to
make explicit.

**Decision.** Confusion matrix and precision/recall/F1 written directly, with zero-division
cases decided explicitly rather than delegated to a `zero_division=` parameter. `undefined`
(nothing was selected) and `0.0` (everything selected was wrong) are different facts and
are reported differently.

---

## 14. Selection threshold is a product decision, not an optimisation

**Context.** A threshold sweep showed F1 flat at 0.67 across thresholds 5, 6 and 7 — the
maths does not pick a winner.

**Decision framing.** At threshold 5, ~43% of digest items are labelled unwanted; at 7,
precision is 0.89 but half the wanted items are missed. For a digest skimmed over coffee,
precision plausibly matters more: a feed that is half noise trains its reader to stop
reading, at which point recall is irrelevant.

**Also discovered.** The model never emits a relevance of exactly 5, so thresholds 5 and 6
select identical sets — the configured value did not mean what the code implied
(`TICKET-028`).

---

## 15. `truncated` field dropped; truncation checks kept

**Context.** Both adapters raise on truncation, which made `LLMResponse.truncated`
provably `False` at every construction site — a field carrying no information
(`TICKET-032`).

**Decision.** Delete the field; keep and strengthen the guards.

**Caveat learned in the process.** A first attempt removed the guards along with the field,
restoring `TICKET-030`'s original symptom. The datum and the check are different things:
the datum was dead, but the check is what converts a downstream `JSONDecodeError` into
*"the model ran out of tokens."* Order matters too — the guard must run **before**
`json.loads`, since a truncated response is malformed precisely because it was truncated.

---

## 16. SDK calls pass every argument explicitly, using provider omit sentinels

**Alternative considered:** building a `dict` and splatting it (`**kwargs`), annotated
`dict[str, Any]` to satisfy the type checker. Rejected because it satisfies by exemption:
mypy then verifies nothing about the call, so a typo'd `max_token` or a `max_tokens="300"`
would pass unchecked at exactly the two places type checking was introduced to protect —
the paid API boundary and the multi-provider seam.

**Decision.** Pass every parameter explicitly, using each SDK's own `Omit` sentinel for
optional values. Both call sites are verified; tests assert
`isinstance(request["temperature"], AnthropicOmit)` rather than merely that a key is absent.

---

## 17. One Protocol, one adapter per wire format

**Alternative considered:** adding a second "universal" client protocol. Rejected because
`LLMClient` already is that interface; a second would mean two contracts to satisfy and no
additional capability.

**Decision.** One stable `LLMClient`, with an adapter per *wire format* rather than per
vendor. An Anthropic Messages adapter plus one OpenAI-compatible Chat Completions adapter
covers vLLM, Ollama, LM Studio, llama.cpp, Together, Groq, OpenRouter and OpenAI, because
they all implement the same shape.

**Correction in flight.** The first OpenAI adapter targeted the *Responses* API, which is
OpenAI-proprietary rather than the interoperability standard. Chat Completions is the
portable surface.

---

## 18. vLLM chosen for the learning goal, not for the workload

**Context.** The local-model phase needs a serving runtime.

**Alternative considered:** Ollama, which would be simpler to stand up and would perform
identically here. Not rejected on merit — it is the better fit for the workload.

**Decision.** vLLM, with the reasoning stated explicitly: this pipeline makes ~40
sequential requests per day with zero concurrency, and vLLM's advantages (PagedAttention,
continuous batching) are throughput optimisations for *concurrent* load. vLLM is chosen
because it is what production inference runs on and understanding the serving layer is a
goal of the project — not because the workload demands it.

**Rationale for recording this.** A choice made for learning value rather than technical
necessity is worth stating as such, so it is not later mistaken for a performance
requirement that was never there.

---

## 19. Delivery: a published static site, not email

**Context.** The original design specified an email digest via SMTP or Resend.

**Alternative considered:** email. Not rejected on capability — it is genuinely better at
*reaching* a reader, since it arrives without being asked for, whereas a page must be
remembered and visited. Rejected on operational and audience grounds: it needs SMTP or a
third-party credential, deliverability is a standing concern, and the output is invisible
to anyone not on the recipient list.

**Decision.** Render to escaped static HTML and publish to GitHub Pages from the same
workflow that runs the pipeline.

**Rationale.** No new credential, no delivery infrastructure, and the artifact is a URL
that can be shared. For a project that doubles as a portfolio piece, a link someone can
open beats an inbox they cannot see.

**Trade accepted.** Pull instead of push: nothing prompts the reader. If daily prompting
turns out to matter, a notification channel can be added *alongside* the page rather than
replacing it.

---

## 20. Digest history: committed HTML snapshots, not a `digest_items` table

**Context.** Showing an archive of past digests requires past digests to persist somewhere.

**Alternative considered:** the `digest_items` table sketched in the original data model,
storing each `DigestItem` as structured rows. Rejected as premature: nothing yet needed to
*query* digest history, only to display it, and the table would have required serialising
`article_urls` into JSON inside SQLite for no present benefit.

**Decision.** Each day's digest renders to a dated HTML file under `docs/`, committed by
the workflow. Git is the archive.

**Consequence — same-day reruns.** Because the filename is date-derived, a second run on
the same calendar day overwrote the first, silently replacing a rich digest with a thinner
one (`TICKET-023`). Timestamped filenames were considered and rejected: they would produce
several confusing same-day entries in the archive. Instead a per-day JSON sidecar
accumulates the day's items and the page is re-rendered from the full set, preserving
one-entry-per-day while making reruns additive.

**Revisit when.** Story continuity needs to *retrieve* past digest content, not display it.
That is the point at which structured storage earns its cost.

---

## 21. No containers or orchestration for the scheduled job

**Context.** Docker and Kubernetes are widely expected on an AI-engineering CV, which is a
reason to learn them but not automatically a reason to use them here.

**Alternative considered:** running the pipeline as a Kubernetes `CronJob`. Rejected on
fit: Kubernetes orchestrates long-running services that need scaling, service discovery and
self-healing. This workload is one script that runs once daily and exits. A managed cluster
would add real monthly cost against a pipeline costing cents; a local cluster would only
fire while a particular machine is switched on, discarding the unattended operation the
project already has.

**Decision.** Keep GitHub Actions cron as the production host. Containerisation is worth
doing as a learning exercise on personal hardware, decoupled from production.

**Rationale.** Adopting infrastructure for CV keywords rather than workload characteristics
is the kind of choice an interviewer probes, and "it runs once a day and exits, so
orchestration buys nothing" is a stronger answer than a cluster nobody needed.

---

## 22. Provider differences reconciled in code, not by an LLM

**Alternative considered:** using a small model to normalise each provider's response into
a common shape, avoiding hand-written adapters. Rejected on several grounds: both response
formats are documented, deterministic structures rather than prose, so this applies a
probabilistic tool to a problem with an exact answer; it would double the LLM calls per
article on a pipeline whose premise is cheap per-article triage; and it reintroduces
precisely the fragility that structured outputs exist to remove — a mis-transcribed
relevance score still validates as a well-formed `TriageResult`, failing silently, whereas
an unexpected shape in an adapter raises immediately.

**Decision.** Hand-written adapters, roughly fifteen lines per provider.

**Boundary that generalises.** Unstructured input to structured output is what an LLM is
uniquely good at — the deferred HTML-extraction scraper is that shape. Structured to
structured is what code does better: cheaper, deterministic, and loud on failure.

---

## 23. Batch API not adopted

**Alternative considered:** the Batch API's 50% discount. Rejected because the saving
applies to a base cost of a few cents per day, while the change is architectural: batch
submission is asynchronous, with completion times ranging from minutes to hours, so a
scheduled job that currently runs and exits would need job tracking, polling, partial
failure handling, and probably a split into submit and collect workflows.

**Decision.** Synchronous calls. Batch is the right tool for high-volume, non-urgent work,
which this is not — the cost problem, if one ever appears, is per-call price, and that is
already addressed by model tiering.

---

## 24. Protocol conformance verified by a type checker, not by structure alone

**Context.** Adapters can satisfy `LLMClient` structurally, without inheriting from it.

**Alternative considered:** structural conformance only, with no type checker. Rejected
because, absent static checking, nothing verifies an adapter actually matches the seam —
and a mismatch surfaces only when a real call is made, potentially against a paid endpoint.

**Also considered:** inheriting from the Protocol *without* a type checker. Rejected as the
worst of both: a Protocol's `...` method bodies are valid implementations returning `None`,
so a missing method instantiates cleanly and fails silently downstream, whereas the purely
structural version at least raises `AttributeError` at the call site.

**Decision.** Adapters inherit from `LLMClient` *and* mypy is part of the toolchain, so
conformance is checked before anything runs. On its first run mypy immediately found a
declared-versus-actual type mismatch at the client seam.

---

## 25. Eval reporting leads with classification flips, not metric deltas

**Context.** Two runs of an identical profile differed by 0.04 F1 and 0.07 recall, which
looks like a meaningful change and is not.

**Alternative considered:** reporting precision/recall/F1 deltas as the primary signal —
the conventional presentation. Rejected at this sample size: with 15 gold-positive articles
in the set, a single article changing verdict moves F1 by 0.04, so aggregate movement is
dominated by noise while *looking* authoritative.

**Decision.** The live report leads with per-article classification flips (`FP->TN`,
`TP->FN`, and so on), with metrics as supporting context.

**Rationale.** Measurement showed triage is ~98% reproducible run to run: an identical
profile moved one article of fifty, while a profile change moved twenty-five. The model is
stable and the metric is volatile, so the article-level view is the trustworthy one. A
change moving fewer than about three articles is indistinguishable from noise regardless of
what F1 reports (`TICKET-034`).

**Prerequisite worth naming.** This is only knowable because the noise floor was measured
deliberately, by running the same profile twice. Without that, every delta stays ambiguous.
