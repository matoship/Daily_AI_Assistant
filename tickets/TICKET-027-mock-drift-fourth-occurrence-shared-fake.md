# TICKET-027: Mock drift, fourth occurrence — fixed structurally with a shared fake

**Category:** mock drift
**Module:** `tests/test_triage.py`, `tests/test_synthesize.py`, `tests/conftest.py`

## Symptom
After the `LLMClient` refactor, the suite was green — but the two fake clients had drifted
from the Protocol and from each other:

| | keyword-only? | `temperature` |
|---|---|---|
| `LLMClient` protocol | yes (`*`) | optional, defaults `None` |
| `test_triage` fake | no | **required** |
| `test_synthesize` fake | no | **absent entirely** |

Both passed only by coincidence: `triage` happens to pass `temperature=0`, `synthesize`
happens not to. Adding `temperature` to synthesize, or removing it from triage, would have
broken a test for reasons unrelated to real behaviour.

## Root cause
The same root cause as TICKET-001, TICKET-003 and TICKET-005: each test hand-rolled its own
stand-in for a dependency, encoding that test author's assumption about the dependency's
shape at the moment it was written. With two independent fakes, the assumptions diverged.

What was different this time: a **formal, written-down contract** now existed
(`protocol.LLMClient`), so for the first time there was something the fakes could be
checked *against* rather than just against each other.

## Fix
One shared `FakeLLMClient` in `tests/conftest.py` mirroring the Protocol exactly —
keyword-only via `*`, `temperature: float | None = None` — exposed through a pytest fixture
that returns the class so each test injects its own canned response. Both tests now use it.
Tests were also switched from `SimpleNamespace` to constructing a real `LLMResponse`, so a
misspelled field raises `TypeError` instead of being silently accepted.

## Lesson
Three previous mock-drift incidents were fixed one at a time, which fixed the instance but
not the cause. **The structural fix only became possible once the dependency had an explicit
interface**: with a Protocol in place, there is exactly one shape to conform to, one shared
fake to maintain, and a change to the contract breaks one place loudly instead of leaving
two fakes to diverge quietly.

Generalisable: when the same class of bug recurs, stop fixing instances and ask what would
make the class impossible. Here the answer was "a named contract plus a single shared fake",
and the Protocol work — done for a completely different reason — is what unlocked it.
