# TICKET-035: Provider and model id were chosen in two places and disagreed

**Category:** design flaw / silent failure
**Module:** `run.py`, `factory.py`, `eval/report.py`

## Symptom
Never observed in production — the branch was not merged. Found by calling the entry point
the way the console script does and printing what reached the pipeline:

| Invocation | Adapter built | Model ids sent |
|---|---|---|
| `daily-assistant` (no flag, what CI runs) | local OpenAI-compatible → `localhost:8000` | Haiku / Sonnet |
| `run()` with its default | Anthropic | `"<vllm model id>"` |

Neither pairing can work. In CI every article would have failed to connect, been logged as
transient, and been skipped — finishing as a `completed` run with zero articles. The whole
test suite was green.

## Root cause
Two independent defects that only interacted at runtime.

**An `argparse.Namespace` was used as a boolean.** `main` passed the parsed namespace into
`run(args)`, which passed it to `build_client(args)`. A `Namespace` is always truthy —
including `Namespace(vllm=False)` — so the local branch was always taken.

**The client and the model ids were selected by two separate expressions that had to
agree**, and the second was written inverted:

```python
client = build_client(args)
if args:
    models = MODELS["anthropic"]
else:
    models = MODELS["local"]
```

Nothing structurally tied the two choices together, so nothing could detect that they had
drifted apart. The same split existed independently in `eval/report.py`, where the client
came from `build_client()` and the model id from `MODELS` directly — so `--vllm` changed the
model without changing the provider.

**Why the tests missed it.** The one test covering this captured the model that reached
`triage_article` and never asserted on it, so it passed against either pairing. It also
called `run(True)` with a real boolean — a value `main` never actually passed.

## Fix
`build_client(local)` returns `(client, models)`: one decision producing both values, so
they cannot disagree. `main` passes `args.vllm`, and `run` takes a typed `local: bool`.
`eval/report.py` unpacks the same pair. `tests/test_factory.py` asserts the pairing, and
the `run` test now asserts the models it captures.

## Lesson
**Two values that must agree should be produced by one expression.** Any design where
correctness depends on two separate statements staying in sync will eventually desynchronise,
and nothing will notice. Returning them together makes the invariant structural instead of
remembered.

**Truthiness is not a type check.** Every ordinary Python object is truthy, so a
`Namespace`, a dict, or an empty-but-present config passes `if x:` exactly like `True`. A
parameter that means "a flag" should be annotated `bool` and receive one.

**A test that captures a value without asserting on it pins nothing.** The captured model
id sat in the assertions dict, unused, through two rounds of review.
