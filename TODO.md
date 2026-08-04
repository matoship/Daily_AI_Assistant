# TODO

## Now (correctness / operations)
- [ ] Fix CI profile: verify `PROFILE_YAML` secret exists with exact name; re-run workflow_dispatch
- [ ] Fail fast on empty/missing profile and sources in `profile.py` (`safe_load` returns `None` for empty file)
- [ ] Failure floor in `run()`: if articles were ingested but zero triaged, raise instead of reporting a completed run
- [ ] Empty-day message in `render_digest_page` ("No relevant news today") so a quiet day is distinguishable from a broken agent
- [ ] Watch `runs` telemetry for a few days: `articles_fetched` suspiciously high may mean Google News redirect URLs are not stable across fetches (would weaken URL dedup)

## Soon (code quality)
- [ ] Digest filename/title uses UTC date, so the 6 AM Adelaide run is stamped with yesterday's date — use `ZoneInfo("Australia/Adelaide")` for display date (keep UTC for storage timestamps)
- [ ] `Storage()` default path `"seen.db"` is CWD-relative — anchor to repo root like `profile._resolve_path`
- [ ] Define a `Protocol` for the LLM client seam (`messages.create`) so `Anthropic | TrackedClient` (and later a vLLM/OpenAI-compatible client) satisfy one honest type
- [ ] Consistent logging style: `logger.info("… %s", x)` lazy formatting everywhere (some f-strings remain)
- [ ] Bump `actions/checkout@v5`; bump `astral-sh/setup-uv` when a Node-24 release lands
- [ ] `telemetry.PRICING`: warn when past Sonnet intro-pricing expiry (2026-08-31); update rates after
- [ ] Drop `_coerce_digest_item` dict-acceptance in `render.py` if nothing produces dicts (single contract)

## Phase 3 (next up)
- [ ] Eval harness: golden set of hand-labeled articles (design the data format first), triage-agreement metric
- [ ] Local LLM on RTX 4090 via vLLM (OpenAI-compatible endpoint), swap into triage behind the client seam, compare against Haiku on the golden set

## Phase 4 (parked)
- [ ] Scraper for migration.sa.gov.au (no RSS exists) — consider Haiku-based structured extraction from HTML
- [ ] Embedding-based story clustering for cross-source near-duplicate merge
- [ ] Feedback loop: per-item thumbs up/down feeding back into profile
- [ ] Email delivery with fully-personal rendering (public page stays sanitized)
