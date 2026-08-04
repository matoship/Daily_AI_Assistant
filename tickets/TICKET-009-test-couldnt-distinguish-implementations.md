# TICKET-009: Test suite couldn't tell old and new selection logic apart

**Category:** false confidence
**Module:** `tests/test_selection.py`

## Symptom
After fixing TICKET-008 (per-category selection), the existing tests still passed — but they would have *also* passed against the old, broken flat-sort implementation.

## Root cause
The original test fixtures put each article in a *different* category, so a flat top-N cut and a per-category top-N cut produce identical results by coincidence. The tests were compatible with two different behaviors, so they pinned neither.

## Fix
Added a fixture that actually exercises the flood scenario: many high-relevance articles in one category plus one lower-relevance article in a second category, and asserted the second category's article survives selection.

## Lesson
A test only has value if there's a plausible *wrong* implementation it would catch. Before trusting a green suite after a behavior change, ask: "would this test still pass if I reverted the fix?" If yes, the test isn't testing the change.
