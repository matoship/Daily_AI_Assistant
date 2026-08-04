# TICKET-007: `synthesize()` crashed on an empty selection

**Category:** edge case
**Module:** `synthesize.py`

## Symptom
On a day with zero selected articles, `synthesize()` would call the Anthropic API with `max_tokens = 800 * 0 = 0`, which the API rejects.

## Root cause
No guard for the empty-input case; `max_tokens` was derived directly from `len(selected_articles)` with no floor.

## Fix
Added `if not selected_articles: return []` at the top of the function, before any API call is constructed.

## Lesson
A "quiet news day" is not an exceptional case for a daily digest agent — it's an expected, routine input that has to be designed for from the start, not patched in reactively. Any function whose behavior scales with `len(input)` should be checked at `len(input) == 0`.
