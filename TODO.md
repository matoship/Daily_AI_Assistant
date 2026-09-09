# TODO

Open work, phased. Phase numbers match `README.md` and `ARCHITECTURE.md`.

Status: **Phases 0–3 complete.** The agent runs unattended and publishes daily; triage
quality is measured against 50 blind-labelled articles with a measured noise floor.
Phase 4 (local-model comparison) is in progress on the `phase-3-vllm` branch.

## Now (correctness / operations)

- [ ] **Sonnet introductory pricing has expired.** `telemetry.PRICING` still carries
      `$2/$10` per MTok; the introductory rate ended 2026-09-01. Real rate is `$3/$15`.
      Every `runs` row and `history.jsonl` entry written since then understates cost by
      ~33%. Update the table, and decide whether past rows are worth backfilling or just
      annotating. Consider making an expiry date a data field rather than a comment, so
      the next lapse fails loudly instead of silently mispricing.
- [ ] **Australian DST shifts the digest an hour** (first Sunday of October). The cron is
      `30 22 * * *` UTC = 08:00 ACST, but becomes 09:00 ACDT. GitHub cron has no timezone
      support, so this is either an accepted annual drift or two dated cron lines.
- [ ] **Failure floor in `run()`**: if articles were ingested but zero triaged, raise
      instead of recording a `completed` run. Currently a run that triages nothing still
      calls `finish_run(status="completed")` — a bad API key would produce exactly this,
      and it would look like a quiet day rather than an outage. Pairs with `LLMConfigError`
      below: config failures should abort, transient ones should skip.
- [ ] **Fail fast on empty profile/sources** (`profile.py`). `load_profile` returns
      `safe_load(f)` unguarded — an empty file yields `None` and fails later somewhere
      unrelated. `load_sources` is worse: `or {}` turns a missing file into an empty source
      list, so the pipeline reports a successful run over zero feeds. Absent config should
      be an error, not an empty value that type-checks.
- [ ] **Detect a missed scheduled run** (`TICKET-022`): GitHub's cron dropped a firing
      silently — no error, no `runs` row. Surface it when no new row appears within a
      window past the scheduled time.

## Phase 4 — local model comparison (in progress)

- [ ] Finish the Chat Completions refactor: two stale assertions in
      `test_adapters.py` still assert the Responses-API tool shape (`tools` and
      `tool_choice`), and `openai._exceptions` is imported but unused.
- [ ] **`LLMError` taxonomy in `protocol.py`** — the seam normalizes response shape but not
      error shape, so `anthropic.*`, `openai.*` and `json.JSONDecodeError` all leak through
      it. Partition by what the caller would do differently (transient / config / protocol),
      translate in the adapter only, chain with `raise ... from exc`. Today `run.py` catches
      bare `Exception` per article, so a rate limit and an `AttributeError` in the adapter
      are indistinguishable.
- [ ] Fix error-check ordering in `OpenAIAdapter`: `finish_reason == "length"` is tested
      *after* the `tool_call is None` check, so a truncated response reports the misleading
      error. `AnthropicLLMClient` gets this right; the OpenAI side inverted it.
- [ ] `strict: True` is sent but unenforceable — neither the triage nor the synthesize
      schema sets `additionalProperties: false`, which OpenAI strict mode requires at every
      object level. Either satisfy it or drop the flag; an unenforced guarantee is worse
      than none.
- [ ] **Prompt caching** before the benchmark, not after. The profile is byte-identical
      across every triage call in a run; cache the prefix and measure the saving with
      existing telemetry. Do it first so the Haiku baseline is measured under the
      configuration actually intended to run.
- [ ] vLLM on the RTX 4090 behind the `LLMClient` seam; benchmark against Haiku on the
      golden set. Needs the home machine.

## Soon (quality / measurement)

- [ ] **Fetch full article text.** `TICKET-029` found a third of triage inputs too thin to
      judge, confirmed by the `input_insufficient` flag in the golden set. This is the
      change most likely to actually move F1 — the bottleneck is input quality, not the
      prompt — and the harness can prove it either way.
- [ ] **The golden set is now ~40% dead weight.** 20 of 50 articles are migration news from
      retired feeds. `Overall` metrics therefore describe a corpus that no longer exists;
      read `Engineering` / `Engineering Sufficient` as the headline until the set is rebuilt
      against the current corpus. (Relative model-vs-model comparison is unaffected — both
      sides see the same dilution.)
- [ ] `Storage()` default `db_path="seen.db"` is CWD-relative — anchor to repo root like
      `profile._resolve_path`. CI has a different working directory.
- [ ] Lazy logging (`logger.info("… %s", x)`) — 11 f-string call sites remain.
- [ ] Bump `actions/checkout@v4` → `v5`; bump `astral-sh/setup-uv@v5` when a Node-24
      release lands.
- [ ] Tag sources with topics in `source.yaml`, validate with Pydantic, and detect orphans
      (a topic with no feeds, or a feed serving no live topic). Would have caught the
      migration-corpus problem months earlier.
- [ ] Bounded-concurrency triage — N sequential calls per run. Forces real thinking about
      rate limits and partial failure; pairs naturally with `LLMError`.

## Phase 5 — semantic memory

- [ ] Embedding-based clustering for cross-source near-duplicate merge and story continuity.

## Phase 6 — agentic upgrade

- [ ] Hand-rolled tool-use loop. Source discovery is the best-motivated first task: propose
      a feed, fetch it, triage a sample, keep it if the hit rate clears a bar.
- [ ] Feedback loop: per-item thumbs up/down feeding back into the profile.

## Recently completed

- [x] Eval harness — 50 blind-labelled articles, precision/recall + flip report, noise floor
      measured, live runs appended to `history.jsonl` (Phase 3, 2026-09).
- [x] `LLMClient` Protocol + adapter/decorator layering (`TICKET-024`).
- [x] `OpenAIAdapter` against the Chat Completions API.
- [x] CI profile secret (`PROFILE_YAML`) — publishing daily since 2026-08.
- [x] mypy clean across `src/`.

## Dropped

- ~~Scraper for `migration.sa.gov.au`~~ — topic retired; the source stopped publishing in
  July and the corpus carried none of the intended signal (`TICKET-031`).
- ~~Watch Google News redirect-URL stability~~ — those feeds were retired with the migration
  topic; no Google News sources remain.
- ~~Email delivery~~ — superseded by the static site (`DECISIONS.md`: a shareable link beats
  an inbox for a portfolio artifact, and needs no SMTP credentials).
