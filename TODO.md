# TODO

Open work, phased. Phase numbers match `README.md` and `ARCHITECTURE.md`.

Status: **Phases 0–3 complete.** The agent runs unattended and publishes daily; triage
quality is measured against 50 blind-labelled articles with a measured noise floor.
Phase 4 (local-model comparison) is in progress on the `phase-3-vllm` branch: the
`LLMError` taxonomy and the provider seam are done, the vLLM run itself is not.

## Now (correctness / operations)

- [ ] **`daily-assistant-sanity --help` runs the paid check** instead of printing usage
      (`TICKET-036`). The module parses no arguments at all, so any flag falls through to
      `build_client()` and a live evaluation. Give it an `argparse` parser like the other
      two commands.
- [ ] **Australian DST shifts the digest an hour** (first Sunday of October). The cron is
      `30 22 * * *` UTC = 08:00 ACST, but becomes 09:00 ACDT. GitHub cron has no timezone
      support, so this is either an accepted annual drift or two dated cron lines.
- [ ] **Failure floor in `run()`**: if articles were ingested but zero triaged, raise
      instead of recording a `completed` run. `LLMConfigurationError` now aborts, which
      covers the bad-API-key case, but a run where every article fails transiently still
      reports success over an empty digest.
- [ ] **Fail fast on empty profile/sources** (`profile.py`). `load_profile` returns
      `safe_load(f)` unguarded — an empty file yields `None` and fails later somewhere
      unrelated. `load_sources` is worse: `or {}` turns a missing file into an empty source
      list, so the pipeline reports a successful run over zero feeds. Absent config should
      be an error, not an empty value that type-checks.
- [ ] **Detect a missed scheduled run** (`TICKET-022`): GitHub's cron dropped a firing
      silently — no error, no `runs` row. Surface it when no new row appears within a
      window past the scheduled time.
- [ ] **Make the pricing expiry data, not a comment** (`TICKET-038`). An expiry that changes
      behaviour should be a date the program compares against, so the next lapse warns
      instead of silently mispricing.

## Phase 4 — local model comparison (in progress)

- [ ] **Make the local endpoint configurable.** `MODELS["local"]` is still the placeholder
      `"<vllm model id>"` and the base URL is hardcoded to `localhost:8000`. Both belong in
      settings or on the CLI — otherwise the model name is changed by editing source.
- [ ] **Record `provider` in `history.jsonl`.** `LLMResponse` now carries it, and the
      comparison is the reason it was added.
- [ ] **Count schema violations as a benchmark result.** Invalid output is now
      `LLMProtocolError` rather than a crash, so "returned unusable output N times of 50" is
      measurable — and it is where small models are expected to lose.
- [ ] vLLM on the RTX 4090 behind the `LLMClient` seam; benchmark against Haiku on the
      golden set. Needs the home machine.
- [ ] **Prompt caching, after vLLM** (`DECISIONS.md` 27). Deferred, not dropped: the
      triage prompt's reusable prefix is ~150 tokens, far below Haiku 4.5's 4096-token
      caching minimum, so provider-side caching would currently no-op without an error.
      Two routes make it real: (a) vLLM's automatic prefix caching, which reuses KV-cache
      blocks with no comparable minimum — measure time-to-first-token with it on and off
      on the 4090; (b) a prefix that genuinely grows past the minimum, e.g. few-shot
      examples — which must not be drawn from the golden set, or the eval scores its own
      answers. Either way, confirm the hit in telemetry (`cache_read_input_tokens` on
      Anthropic) rather than assuming it.

## Soon (quality / measurement)

- [ ] **Remaining seam tests.** A cross-adapter parity test (same failure, same `LLMError`
      subclass from both adapters); a malformed-JSON adapter test — the behaviour is
      correct but pinned by nothing; and an invariant that no module outside `adapters.py`
      and `factory.py` imports `anthropic` or `openai`.
- [ ] **Unknown provider errors are labelled protocol errors.** Anything not enumerated in
      the transient or config tuples falls through to `LLMProtocolError`, which catches
      Anthropic's 529 `OverloadedError` and 503 `ServiceUnavailableError` — the most common
      transient failures in practice. Behaviour is identical today (both are skipped), but
      the logs name the wrong cause. Consider enumerating only the closed config set and
      treating the remaining `APIError` as transient.
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
- [ ] Lazy logging (`logger.info("… %s", x)`) — f-string call sites remain in `run.py` and
      `eval/sanity.py`.
- [ ] Bump `actions/checkout@v4` → `v5`; bump `astral-sh/setup-uv@v5` when a Node-24
      release lands.
- [ ] Tag sources with topics in `source.yaml`, validate with Pydantic, and detect orphans
      (a topic with no feeds, or a feed serving no live topic). Would have caught the
      migration-corpus problem months earlier.
- [ ] Bounded-concurrency triage — N sequential calls per run. Forces real thinking about
      rate limits and partial failure; the `LLMError` taxonomy is the prerequisite and is
      now in place.

## Phase 5 — semantic memory

- [ ] Embedding-based clustering for cross-source near-duplicate merge and story continuity.

## Phase 6 — agentic upgrade

- [ ] Hand-rolled tool-use loop. Source discovery is the best-motivated first task: propose
      a feed, fetch it, triage a sample, keep it if the hit rate clears a bar.
- [ ] Feedback loop: per-item thumbs up/down feeding back into the profile.

## Recently completed

- [x] **`LLMError` taxonomy at the client seam** — transient / configuration / protocol,
      translated in the adapters, chained with `from exc`; schema violations converted at
      the parse boundary; `provider` added to `LLMResponse`. Config errors now abort the
      run, transient and protocol errors skip one article (`TICKET-037`).
- [x] **Provider selection unified** — `build_client(local)` returns `(client, models)` so
      the adapter and the model ids cannot disagree (`TICKET-035`).
- [x] **Entry-point invariant test** derived from `[project.scripts]` (`TICKET-036`).
- [x] Sonnet pricing corrected to the standard rate (`TICKET-038`).
- [x] `OpenAICompatibleAdapter` against the Chat Completions API; `strict: true` dropped
      rather than carried unenforced.
- [x] Error-check ordering in the OpenAI adapter — truncation is tested before the
      missing-tool-call check, so the reported cause is the real one.
- [x] Eval harness — 50 blind-labelled articles, precision/recall + flip report, noise floor
      measured, live runs appended to `history.jsonl` (Phase 3, 2026-09).
- [x] `LLMClient` Protocol + adapter/decorator layering (`TICKET-024`).
- [x] CI profile secret (`PROFILE_YAML`) — publishing daily since 2026-08.
- [x] mypy clean across `src/`.

## Dropped

- ~~Scraper for `migration.sa.gov.au`~~ — topic retired; the source stopped publishing in
  July and the corpus carried none of the intended signal (`TICKET-031`).
- ~~Watch Google News redirect-URL stability~~ — those feeds were retired with the migration
  topic; no Google News sources remain.
- ~~Email delivery~~ — superseded by the static site (`DECISIONS.md`: a shareable link beats
  an inbox for a portfolio artifact, and needs no SMTP credentials).
