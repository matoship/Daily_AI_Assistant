# TICKET-033: An untested writer would have discarded a paid evaluation run

**Category:** silent failure / test coverage gap
**Module:** `eval/report.py`

## Symptom
Caught in review, before the first live evaluation run:

```
TypeError: Object of type dict_keys is not JSON serializable
```

`write_report_to_file` is the final step of `--live` mode. It runs *after* fifty real
Haiku calls have been made, all metrics computed, and all flips calculated. A crash there
loses the entire run's result while still incurring its full cost.

## Root cause
```python
model_id = client_usage.keys()      # dict_keys view, not a list
```

`json.dumps` cannot serialise a `dict_keys` view. The field had just been added — correctly
motivated, since the branch exists to compare Haiku against a local model and a history
record that does not name the model cannot support that comparison — but the value was the
view object rather than its contents.

The 31-test suite passed throughout. `grep write_report_to_file tests/` returned **zero**
matches: the function that persists the result of an expensive, hard-to-repeat operation
had no test at all.

## Fix
- `model_id = list(client_usage.keys())`.
- Round-trip test: write to a `tmp_path`, read the line back, assert the record parses and
  carries `model_id`, `metrics_result`, and a non-zero `cost_estimate`.

## Lesson
**Third occurrence of the same pattern: the untested function is the one that breaks.**
`ingest()` was broken against the real `Storage` while its test mocked the call away
(TICKET-006). `adapters.py` shipped with a wrong kwarg and a swallowed temperature before
it had tests. Now the history writer. In each case the suite was green and the untested
seam was the failure.

**Weight test coverage by cost of failure, not by complexity.** `write_report_to_file` is
twenty trivial lines — dict construction and a file append — which is exactly why it looked
like it did not need a test. But it sits at the end of the only operation in the project
that costs real money and cannot be cheaply repeated. Triviality is a poor proxy for
whether something deserves a test; blast radius is a better one.

**A `dict_keys` view is not a list.** It renders convincingly in a debugger, supports
iteration and `in`, and fails only at the serialisation boundary — so it survives every
check short of actually writing the file.
