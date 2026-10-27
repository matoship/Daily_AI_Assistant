# TODO

Open work, phased. Phase numbers match `README.md` and `ARCHITECTURE.md`.

Status: **Phases 0–3 complete.** The agent runs unattended and publishes daily; triage
quality is measured against 50 blind-labelled articles with a measured noise floor.
Phase 4 (local-model comparison) is in progress on the `phase-3-vllm` branch: the
`LLMError` taxonomy and the provider seam are done, and Qwen3-4B is serving on vLLM 0.29.0
behind the seam. The Haiku comparison is blocked on the triage `length` failures and an
unmeasured vLLM noise floor (Phase 4, below).

## Now (correctness / operations)

- [ ] **State is committed before delivery** (`TICKET-041`). `run()` marks articles
      `digested` and records the run `completed` before `main()` writes any output, so any
      later exception loses the digest and the `runs` row reports success. This happened
      twice (runs 41, 43). Decide what `digested` and `completed` must mean, then move the
      commits after the write, or add an intermediate state a retry can pick up.
- [ ] **7 articles are `digested` with no page** (runs 41, 43; `TICKET-041`). Nothing will
      reselect them. Decide whether to recover them (reset to a retryable status) or
      accept the loss, and record which.
- [ ] **Interrupted runs stay `running` forever.** Ctrl+C raises `KeyboardInterrupt`, which
      is a `BaseException` and bypasses `run()`'s `except Exception`, so `finish_run` never
      executes. Four such rows exist (34, 35, 39, 44). A `finally` (or a `BaseException`
      branch that records `interrupted` and re-raises) would close them.
- [ ] **Local runs write the production state.** CI commits `seen.db` and `docs/`
      (`daily-digest.yaml`), and local `--vllm` runs write the same files: Qwen-scored
      articles, zombie runs, the lost digests and an uncommitted 2026-10-28 page are in the
      working tree now. Back up the experiment database, then decide before the next
      commit whether to restore `seen.db` and `docs/`. Longer term, local and eval runs
      need their own database path (see the `Storage()` item under *Soon*).
- [ ] **Australian DST shifts the digest an hour** (first Sunday of October). The cron is
      `30 22 * * *` UTC = 08:00 ACST, but becomes 09:00 ACDT. GitHub cron has no timezone
      support, so this is either an accepted annual drift or two dated cron lines.
- [ ] **Failure floor in `run()`**: if articles were ingested but zero triaged, raise
      instead of recording a `completed` run. `LLMConfigurationError` now aborts, which
      covers the bad-API-key case, but a run where every article fails transiently still
      reports success over an empty digest. Not yet observed end to end: the one
      server-down run (39) was interrupted before `finish_run`. Run it once with vLLM
      stopped from the start and let it finish (~10 min) before designing the floor.
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

- [ ] **Triage `length` failures on Qwen: 30–75% of articles per run.** The model hits
      `max_tokens=600` inside `reason` and never closes the tool call. Two causes combine:
      - **Prompt/schema mismatch.** The prompt asks for "story hints", the schema has no
        field for them, and nothing bounds `reason`. Truncated outputs visibly ramble about
        "the story hints".
      - **Near-tie divergence.** At `temperature=0` the same request takes the rambling path
        or the clean one depending on server state: a cold prefix cache (5/5 `length` with
        a fresh `cache_salt`, 0/5 warm), batch composition (30/30 `length` at 10 concurrent,
        0/20 sequential) and server restart (144 vs 232 tokens, same flags).

      Some articles fail on every attempt with a warm cache (Baidu OCR 2, Nanbeige4.3 and
      tsrs failed in runs 43 and 45), so retrying does not help. Fix the prompt and schema
      first. Regression checks: zero `length` on the cold row of `salt.py 5` and on
      `hammer.py 30 10`. Write the ticket when it is fixed.
- [ ] **Measure the vLLM noise floor before comparing models.** The ~98% reproducibility
      figure was measured on Haiku. On vLLM, output depends on hidden server state (above),
      and the first article of every run sees a cold cache. Run `report --live --vllm`
      twice with a server restart between, count classification flips, and only then
      compare Qwen with Haiku (read flips, not F1 deltas; `TICKET-034`).
- [ ] **Nothing enforces the tool schema on the vLLM path.** The hermes parser extracts the
      tool call from free text *after* generation; no structured-output constraint is
      applied, so `enum` and `required` are requests, not guarantees. 2 of 7 golden-set
      captures returned a `reason` ending in stray characters (`…career goals.', `) that
      passed `json.loads` *and* `TriageResult`. Evaluate vLLM structured outputs, and
      treat "validated" as weaker than "correct".
- [ ] **The truncation error discards its own evidence.** On `finish_reason == "length"`
      the adapter raises without `completion_tokens` or any excerpt of the text, and its
      message ("Consider increasing max_tokens") points at the wrong fix: a longer budget
      only lets the model ramble longer. Carry the evidence on the exception and log it
      (`TICKET-030`: a signal nothing records is not observability).
- [ ] **A 400 is not one kind of failure.** `BadRequestError` maps to
      `LLMConfigurationError` and aborts the run. That is right for a server
      misconfiguration (`TICKET-039`: every request fails) and wrong for a prompt longer
      than `--max-model-len` (one article fails; the rest are fine). Status code alone
      cannot tell them apart; decide what can, by blast radius, and record it in
      `DECISIONS.md`.
- [ ] **Persistently failing articles are retried silently until they expire.** A failed
      article stays `fetched` and is retried each run (one full 600-token generation per
      attempt) until the 48-hour sweep marks it `outdated`. A relevant article that always
      fails is never reported as missing. Count attempts, or surface the expiry.
- [ ] **Local runs log a pricing warning.** `Pricing for model Qwen/... not found` on every
      run. Decide whether a local model is explicitly $0 or explicitly unpriced, so cost
      telemetry does not mix "free" with "unknown".
- [ ] **Stale sanity fixture.** `obvious-relevant-immigration` expects relevance the current
      profile no longer asks for (topic retired, `TICKET-031`); it now fails correctly.
- [ ] **`VLLM_BASE_URL` uses `localhost`.** On Windows a refused connection takes ~4.2 s via
      `localhost` (both address families tried in turn) vs ~2.05 s via `127.0.0.1`, so a
      server-down run spends ~13.5 s per article. Minor; `127.0.0.1` halves it.
- [ ] **Healthcheck container reachability is unverified.** vLLM binds `--host 127.0.0.1`;
      from inside a container that address is the container itself. Confirm the check
      can reach the server before relying on it.
- [ ] Benchmark Qwen3-4B against Haiku on the golden set, once the `length` failures are
      fixed and the noise floor is measured (both above).
- [ ] **Prompt caching, after vLLM** (`DECISIONS.md` 27). Deferred, not dropped: the
      cacheable prefix — tool schema plus instructions and profile — is ~260–300 tokens,
      about 7% of Haiku 4.5's 4096-token minimum and roughly 13× short of it, so
      provider-side caching would currently no-op without an error.
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
      `profile._resolve_path`. CI has a different working directory. Make the path
      configurable at the same time, so local and eval runs stop writing the production
      database (see *Local runs write the production state*, above).
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

- [x] **`tzdata` added as a dependency** — Windows has no system time-zone database, so
      `main()` crashed after the pipeline finished (`TICKET-041`; the ordering flaw it
      exposed is open, above).
- [x] **vLLM serving flags documented** — `--enable-auto-tool-choice` gates whether
      `--tool-call-parser` loads at all (`TICKET-039`); `VLLM_USE_FLASHINFER_SAMPLER=0`
      avoids a FlashInfer JIT build against a CUDA 12.0 `nvcc` (`TICKET-040`).
- [x] **Coverage in the report** — `format_report` prints scored/failed counts, so a model
      that fails more cannot look better by being scored on fewer articles.
- [x] **Local settings validated in `build_client`** — missing `LOCAL_MODEL`,
      `VLLM_BASE_URL` or `LOCAL_API_KEY` raises at construction; model ids resolve inside
      the function, not at import.
- [x] **`daily-assistant-sanity` has an `argparse` parser** — `--help` prints usage instead
      of running the paid check (`TICKET-036`).
- [x] **Local endpoint is configurable** — `VLLM_BASE_URL`, `LOCAL_API_KEY` and
      `LOCAL_MODEL` come from settings; no model id in source.
- [x] **Triage failures are collected and persisted** — `evaluate_live` returns
      `(rows, errors)` with a `TriageFailure` per unusable response, written to
      `history.jsonl`. Surfacing them in the report is still open, above.
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
