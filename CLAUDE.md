# Daily AI Assistant

Autonomous personal news agent. Fetches RSS feeds, triages every article against a private
profile with Claude Haiku, selects per-category, synthesizes a personalized digest with
Claude Sonnet, renders it to HTML, and publishes to GitHub Pages — unattended, daily, via
GitHub Actions cron.

Not a summarizer. Every relevance decision is grounded in Kaifeng's actual situation
(Adelaide-based, targeting AI Application Engineer / Forward Deployed Engineer roles).
If a change would make the output generic, it is the wrong change.

## Working agreement — read this first

**Kaifeng is learning, and that outranks shipping.** He is escaping "vibe coding" —
AI-generated code he cannot explain or defend — to become interview-ready. He must be
able to defend every line of the load-bearing code.

**He writes:** prompts, structured outputs, the pipeline, storage, retrieval, evals —
anything that carries a concept worth owning in an interview.

**Claude does:**
- Concept briefings before he codes (what the idea is, why it matters, the tradeoffs)
- Interface sketches — **signatures, not implementations**
- PR-style review of his code: root cause + the generalizable lesson, not just a fix
- Hints before answers. Let him hit the bug; then explain why it happened.

**Claude writes code only when asked**, and then only: boilerplate, throwaway
verification scripts, presentation/CSS, and documentation. Never the core pipeline
logic — writing it for him defeats the entire purpose of the project.

**Verify claims against the code, not the writeup.** Reviews here have repeatedly found
that a stated fix did not land, or landed in a way that recreated the original flaw
(`TICKET-032`). Run it, print it, check it.

When reviewing tests, always ask: *would this test fail against the wrong
implementation?* If not, it pins nothing. This has caught real bugs here repeatedly.

## Commands

```bash
uv run pytest -q                  # test suite (fast, mocked, no API cost)
uv run mypy src/                  # type check
uv run daily-assistant            # full pipeline: fetch → digest → docs/ (~1-2c)
uv run daily-assistant-sanity     # eval sanity fixtures against live triage (~1c)
uv run daily-assistant-report     # score triage vs golden set (offline free, --live ~13c)
```

Python 3.12, uv, `src/` layout. Always import the installed package name
(`from daily_assistant.x import y`) — never bare module names (a bare `profile`
collides with the stdlib).

## Architecture

```
source.py     fetch RSS/Atom → Article
pipeline.py   ingest: dedup via article status lifecycle
triage.py     score each article vs profile          [Haiku]
selection.py  threshold filter + per-category top_n  (pure)
synthesize.py merge related stories → DigestItem     [Sonnet]
render.py     DigestItem → escaped HTML              (pure)
run.py        composition root; main() does I/O

protocol.py   LLMClient Protocol + LLMResponse dataclass
adapters.py   AnthropicLLMClient — adapts SDK → LLMClient
telemetry.py  TrackedClient decorator + cost estimation
factory.py    build_client() — the only place a provider is named
storage.py    SQLite: articles / runs / triage_logs
eval/         golden set, sanity fixtures, labeler, precision/recall report
```

**Client layering** (order matters — see `TICKET-024`):
`Anthropic` → `AnthropicLLMClient` (**adapter**, normalizes provider shape) →
`TrackedClient` (**decorator**, preserves the `LLMClient` interface).

The adapter must sit innermost. Telemetry then reads flat `LLMResponse` fields and works
unchanged for any provider; put it inside the adapter and it needs per-provider branching
(`usage.input_tokens` vs `usage.prompt_tokens`). Built once in `factory.build_client()`.

**Topics are data, not code.** `category_options()` derives the triage category enum from
`profile.yaml`'s `topics` keys. Adding or removing a topic needs no code change — but
sources are not yet tagged by topic, so orphans are not detected automatically.

**Article status lifecycle** — `status` records an *outcome*, never a derivable fact:
```
(new) → fetched → scored → digested   [terminal]
            ↓
        outdated                      [terminal]
```
Only `fetched` is swept by the 48h `mark_outdated_before` — it is the only limbo state.
`fetched` stays eligible for retry, which is what makes a crashed run recoverable.

## Conventions (each learned from a real bug — see `tickets/`)

- **Fail fast.** Constraints are tripwires. Absent config arrives as an empty value that
  type-checks, not as an error (`Field(..., min_length=1)`).
- **Mocks must match the real dependency's shape**, not the code's assumption about it.
  Shared fakes live in `tests/conftest.py` and conform to the Protocol.
- **Test by blast radius, not complexity.** The untested function is the one that breaks —
  three times now. Twenty trivial lines at the end of a paid operation deserve a test more
  than a clever pure function does (`TICKET-033`).
- **A computed signal nothing reads is not observability.** Adding a field is half the
  work; the other half is a consumer (`TICKET-030`, `TICKET-032`).
- **Named SQL params** (`:cutoff`), never positional — adding a placeholder silently
  shifts every parameter after it.
- **State tables and event logs stay separate.** `articles` is overwritten; `triage_logs`
  is append-only. Conflating them invites upsert bugs (`TICKET-011`).
- **`__file__`-anchored paths**, never CWD-relative — CI has a different working dir.
- **Escape untrusted text** (`html.escape`) before it reaches a rendered page. LLM output
  and feed titles are untrusted.
- **UTC for storage timestamps**, local (`Australia/Adelaide`) only for display dates.
- **Pre-flight every new feed.** It must parse, return entries, and carry real summary
  text — not an echoed headline. Two dead feeds and a spam feed were caught this way
  before being added (`TICKET-031`).
- **Log at every stage boundary.** Two production incidents were diagnosed from a single
  `runs` telemetry row before any log was read.

## Reading eval results

- Triage is ~98% reproducible run to run; **one** article changing moves overall F1 by
  0.04, because only 15 of the 50 golden-set articles are gold-positive.
- **Read classification flips, not metric deltas.** A change moving fewer than ~3 articles
  is indistinguishable from noise (`TICKET-034`).
- The frozen `model_relevance` in `golden_set.yaml` predates later schema changes. It is
  history, not a comparator — compare against the most recent live run in `history.jsonl`.

## Docs

| Path | What |
|---|---|
| `tickets/` | 34 postmortems: symptom → root cause → fix → lesson. Claude maintains these. |
| `TODO.md` | Open work, phased. |
| `ARCHITECTURE.md` | Deeper design notes. |
| `DECISIONS.md` | 20 decisions with rejected alternatives; ⚖️ marks contested ones. |
| `notes/` | Kaifeng's own learning notes. **Gitignored** — local only. |

Add a ticket whenever a real incident is closed. Keep it factual: what broke, why, how
it was fixed, and the generalizable lesson.

Add an entry to `DECISIONS.md` whenever a design choice is settled and a real alternative
was rejected — a milestone, a seam, a schema, a methodology. Record the rejected option and
why it lost, not just the winner; a decision log that only lists winners is a changelog.

Keep it **impersonal and public-facing**: "Alternative considered: X. Rejected because Y."
Never narrate who proposed or opposed what — the repo is public, and the engineering
reasoning is the durable part. A personal record of disagreements belongs in `notes/`.

**Tickets and decisions are different.** A ticket is something that *broke*; a decision is a
choice between options that *existed*. Some incidents produce both (`TICKET-024` →
decision 6) — cross-reference, don't duplicate.

## State

Phases 0–3 complete. The agent runs unattended and publishes daily; triage quality is
measured against 50 blind-labelled articles, with a measured noise floor.

Scope narrowed in September 2026: the skilled-migration half was retired after evaluation
showed those feeds carried essentially none of the intended signal, and the authoritative
source had stopped publishing (`TICKET-031`). Four pre-flight-tested engineering sources
remain. `profile.yaml` may still carry a dormant `immigration` topic with no feeds behind
it — a decision left open.

Next: `OpenAIAdapter` behind the `LLMClient` seam, then a local model on an RTX 4090 via
vLLM benchmarked against Haiku on the golden set. After that: embeddings for near-duplicate
merge, then a hand-rolled agent loop (source discovery is the best-motivated first task —
propose a feed, fetch it, triage a sample, keep it if the hit rate clears a bar).
