# TICKET-026: Half-finished adapter refactor plus a name-shadowing `UnboundLocalError`

**Category:** regression / Python semantics
**Module:** `synthesize.py`

## Symptom
`test_synthesize` failed with:

```
UnboundLocalError: cannot access local variable 'AnthropicLLMClient'
where it is not associated with a value
```

## Root cause
Two problems stacked in a partially-completed refactor.

**1. Name shadowing.** The line was:
```python
AnthropicLLMClient = AnthropicLLMClient(client)
```
Assigning to a name *anywhere* in a function body makes that name local for the **entire**
function, including lines that execute before the assignment. So the right-hand side no
longer resolved to the imported class — it resolved to a local that did not yet exist.

**2. The refactor changed the call target but not the arguments.** The call was switched
from `client.messages.create(...)` to the adapter's `create(...)`, but still passed the
old raw Anthropic kwargs (`tools=[...]`, `tool_choice=...`, `messages=[...]`) instead of
the adapter's `prompt` / `tool_name` / `tool_description` / `tool_schema`. It also still
read `response.tool_use_block.input`, a field `LLMResponse` does not have (`tool_input`).
Even past the `UnboundLocalError`, this would have been a `TypeError` then an
`AttributeError`.

## Fix
Renamed the local to `llm_client`, converted the arguments to the adapter's signature,
and read `response.tool_input`. Later superseded entirely by constructing the adapter at
the composition root (`run.py`) and passing `LLMClient` down, so `synthesize` stopped
importing `Anthropic` or `AnthropicLLMClient` at all.

## Lesson
Python's scoping rule here is worth memorising: **assignment anywhere in a function makes
the name local throughout that function** — `X = X(...)` never means "wrap the global X",
it always means "read the local X that doesn't exist yet." Never reuse an imported name
as a local variable.

On the refactor itself: changing a call's *target* and its *arguments* are two separate
edits, and doing only the first leaves code that looks converted but cannot run. When
moving call sites onto a new interface, the signature is the checklist — walk every
argument, not just the function name.
