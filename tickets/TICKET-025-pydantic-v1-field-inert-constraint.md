# TICKET-025: `pydantic.v1` import made a validation constraint silently inert

**Category:** silent failure / fail-fast gap
**Module:** `config.py`

## Symptom
`Settings` declared `anthropic_api_key: str = Field(..., min_length=1)` — the fix applied
after TICKET-021 to make an empty API key fail loudly at startup. Verified directly:

```python
Settings(anthropic_api_key='')   # → NO ERROR, value accepted as ''
```

The guard looked present in the source and did nothing.

## Root cause
`config.py` imported `from pydantic.v1 import Field` — the **v1 compatibility shim**
bundled inside Pydantic v2 — while `Settings` is a Pydantic-v2 `BaseSettings`. A v1
`FieldInfo` object is not what v2's model construction expects, so the `min_length=1`
constraint was never registered. No error was raised at import or at class definition;
the annotation simply had no effect.

Every other module in the project imports `Field` from plain `pydantic`, so this file
was the lone inconsistency.

## Fix
`from pydantic import Field`. Re-ran the same check; it now raises `ValidationError`.

## Lesson
A fix that is *present in the source* is not the same as a fix that is *in effect* —
especially for declarative constraints, which produce no output when they work and no
output when they don't. **Verify a fail-fast guard by actually triggering it once**
(`Settings(anthropic_api_key='')`) rather than trusting that the line exists.

Also: mixing v1 and v2 APIs of the same library is a silent-failure generator, because
the shim is *designed* to be importable and superficially compatible. Import consistency
across modules is worth enforcing for its own sake.
