# TICKET-032: The truncation flag became unreachable in the fix for TICKET-030

**Category:** dead code / unused signal
**Module:** `adapters.py`, `protocol.py`

## Symptom
None observed. Found while verifying the fixes TICKET-030 claimed, by checking each one
against the code rather than reading the writeup.

## Root cause
TICKET-030's lesson was that `LLMResponse.truncated` was computed but never read, so a
truncated response surfaced two layers away as a confusing missing-field error. The fix
added a guard — but placed it in `AnthropicLLMClient.create` *before* the response object
is constructed:

```python
if response.stop_reason == "max_tokens":
    raise ValueError("max_tokens are met before the model could finish its response...")
...
return LLMResponse(
    ...
    truncated=response.stop_reason == "max_tokens",   # can only ever be False here
)
```

Execution cannot reach the constructor with `stop_reason == "max_tokens"`, so `truncated`
is now permanently `False`. Verified: a truncated response raises before any `LLMResponse`
exists, and a normal response yields `truncated=False`. Nothing in the codebase reads the
field.

So the field is in exactly the state TICKET-030 was written about — computed, carried
through the protocol, consumed by nobody — except it is now also structurally incapable of
being true.

## Fix
Two coherent options; the raise and the flag should not both exist:

- Keep the adapter's raise (fail loud, every caller protected by default) and delete
  `truncated` from `LLMResponse`.
- Or drop the raise and let callers check the flag, which lets `synthesize` handle
  truncation differently from `triage` — for instance by retrying with a larger budget
  rather than failing the run.

## Lesson
**A fix can recreate the flaw it was written about.** TICKET-030 correctly diagnosed
"a computed signal that nothing reads is not observability", then shipped a guard that left
the same signal computed and unread — this time unreachable as well. Writing the lesson
down does not apply it.

**Guard placement decides who gets to choose.** Raising inside the adapter is the right
default for a nightly job, but it removes the caller's ability to respond differently. That
is a design decision worth making deliberately rather than inheriting from wherever the
`if` happened to land.

**Verify claimed fixes against the code, not the writeup.** Three of TICKET-030's four
claims held exactly; this one did not, and only checking each line against the source
showed it.
