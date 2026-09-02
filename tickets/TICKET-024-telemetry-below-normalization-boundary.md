# TICKET-024: Telemetry decorator sat below the provider-normalization boundary

**Category:** design flaw
**Module:** `run.py`, `telemetry.py`, `adapters.py`

## Symptom
No runtime failure. Caught in design review: the client stack was assembled as
`Anthropic → TrackedClient → AnthropicLLMClient`, which would have silently produced
**zero telemetry on any non-Anthropic provider** the moment a vLLM adapter was added.

## Root cause
`TrackedMessages.create` read `response.model`, `response.usage.input_tokens`, and
`response.usage.output_tokens` — the *Anthropic SDK's* response shape. Sitting
underneath the adapter, it could only ever understand one provider's responses.
An OpenAI-compatible response uses `usage.prompt_tokens` / `usage.completion_tokens`,
so the same tracker would have thrown or recorded nothing.

The wrapping order had been chosen by reasoning about *what mechanically wraps what*
(`TrackedClient` needs a `.messages` attribute, so it must sit next to the SDK)
rather than about *which interface each layer should depend on*.

## Fix
Moved `TrackedClient` outside the adapter: `Anthropic → AnthropicLLMClient → TrackedClient`.
It now receives an already-normalized `LLMResponse`, whose `model` / `input_tokens` /
`output_tokens` fields are provider-neutral by construction, so one tracker serves every
adapter. `TrackedMessages` was deleted — `TrackedClient` became a single class
implementing `LLMClient` directly. `run.py` also simplified from two client variables
to one, since the tracker is now the outermost object and is both what gets passed down
and what gets read for the telemetry row.

## Lesson
**Put shared, cross-provider behavior *above* the normalization boundary, never below it.**
An adapter exists to erase vendor differences; anything generic that sits underneath it
inherits those differences permanently and has to be reimplemented per vendor.

Secondary lesson about layering order generally: the question to ask is not "what can
physically wrap what" but "which interface should this layer be written against." The
mechanical constraint (`TrackedClient` needed `.messages`) was a *symptom* of the wrong
choice, not a reason for it — once the tracker was rewritten against `LLMClient`, the
constraint disappeared entirely.
