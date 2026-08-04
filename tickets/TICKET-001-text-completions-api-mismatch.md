# TICKET-001: Text Completions API mismatch (`response.completion`)

**Category:** mock drift
**Module:** `triage.py`

## Symptom
`triage_article` raised `AttributeError` accessing `response.completion`.

## Root cause
The code was written against the old Anthropic Text Completions API shape. The real Messages API returns `response.content`, a list of typed blocks (`tool_use` among them), not a flat `.completion` string.

## Fix
Switched to reading `response.content`, finding the `tool_use` block, and using its already-parsed `.input` dict.

## Lesson
The unit test for this function *also* mocked `.completion` — so it passed while the real integration was broken. A mock encodes an assumption about a dependency's shape; if the assumption is wrong, the test agrees with the broken code instead of catching it. The fix isn't just correcting the code — it's re-deriving the mock from the real API response shape, not from what the code currently expects.
