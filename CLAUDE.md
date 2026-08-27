# Daily AI Assistant

Autonomous personal news agent. Fetches RSS/Google-News feeds, triages every article
against a private profile with Claude Haiku, selects per-category, synthesizes a
personalized digest with Claude Sonnet, renders it to HTML, and publishes to GitHub
Pages — unattended, daily, via GitHub Actions cron.

Not a summarizer. Every relevance decision is grounded in Kaifeng's actual situation
(Adelaide-based, skilled-migration pathway, targeting AI Application Engineer roles).
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

When reviewing tests, always ask: *would this test fail against the wrong
implementation?* If not, it pins nothing. This has caught real bugs here repeatedly.

## Commands

```bash
uv run pytest -q                  # test suite (fast, mocked, no API cost)
uv run daily-assistant            # full pipeline: fetch → digest → docs/ (~15-25c)
uv run daily-assistant-sanity     # eval sanity fixtures against live triage (~1c)
```

Python 3.12, uv, `src/` layout. Always import the installed package name
(`from daily_assistant.x import y`) — never bare module names (a bare `profile`
collides with the stdlib).

## Architecture

```
source.py     fetch RSS/Atom → Article
pipeline.py   ingest: dedup (cross-run via status, within-run via set)
triage.py     score each article vs profile        [Haiku]
selection.py  threshold filter + per-category top_n   (pure)
synthesize.py merge related stories → DigestItem    [Sonnet]
render.py     DigestItem → escaped HTML             (pure)
run.py        composition root; main() does I/O

protocol.py   LLMClient Protocol + LLMResponse dataclass
adapters.py   AnthropicLLMClient — adapts SDK → LLMClient
telemetry.py  TrackedClient decorator + cost estimation
storage.py    SQLite: articles / runs / triage_logs
```

**Client layering** (order matters — each wrapper consumes the interface below it):
`Anthropic` → `TrackedClient` (decorator, preserves interface) → `AnthropicLLMClient`
(adapter, changes interface). Built once in `run.py`; `LLMClient` is passed down.

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
- **Named SQL params** (`:cutoff`), never positional — adding a placeholder silently
  shifts every parameter after it.
- **`__file__`-anchored paths**, never CWD-relative — CI has a different working dir.
- **Escape untrusted text** (`html.escape`) before it reaches a rendered page. LLM output
  and feed titles are untrusted.
- **UTC for storage timestamps**, local (`Australia/Adelaide`) only for display dates.
- **Comprehensions for pure transforms only** — the moment a side effect is needed
  (logging, marking), use a loop.
- **Log at every stage boundary.** Two production incidents were diagnosed from a single
  `runs` telemetry row before any log was read.

## Docs

| Path | What |
|---|---|
| `tickets/` | 23 postmortems: symptom → root cause → fix → lesson. Claude maintains these. |
| `TODO.md` | Open work, phased. |
| `ARCHITECTURE.md` | Deeper design notes. |
| `notes/` | Kaifeng's own learning notes. **Gitignored** — local only. |

Add a ticket whenever a real incident is closed. Keep it factual: what broke, why, how
it was fixed, and the generalizable lesson.

## State

Phase 2 complete: the agent runs unattended and publishes daily. Phase 3 in progress —
eval harness. `eval/sanity_fixtures.yaml` (mechanical plumbing check, real articles, not
ground truth) exists and passes; `eval/golden_set.yaml` is **empty and deliberately so** —
it needs human-labeled ground truth, which is the gate for measuring triage quality and
for any honest local-model comparison. Do not fill it with LLM-generated labels: that
measures agreement with another model, not with Kaifeng.

Next: local LLM on RTX 4090 via vLLM behind the `LLMClient` seam (needs an adapter —
OpenAI-compatible servers expose `.chat.completions.create`, not `.messages.create`),
Docker, then k8s CronJob.
