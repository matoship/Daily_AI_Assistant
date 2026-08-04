# TICKET-015: `published_at` carried a stale value across feed entries

**Category:** silent data bug
**Module:** `source.py`

## Symptom
Some articles were stored with a `published_at` date that belonged to a *different* article entirely — wrong data, no error.

## Root cause
```python
parsed = entry.get("published_parsed")
if parsed:
    published_at = datetime(*parsed[:6])
# no else branch
```
When an entry lacked a publish date, `published_at` simply kept whatever value it held from the *previous* loop iteration, because the variable was never reset. If entry 1 had a date and entry 2 didn't, entry 2 silently inherited entry 1's timestamp.

## Fix
Added `else: published_at = None`.

## Lesson
This is a more dangerous failure mode than a missing-date crash would have been — a `NameError` on the first entry would at least be loud. A variable reused across loop iterations without being reset on every branch will leak stale state whenever a conditional doesn't cover every case. Any `if` that sets a variable used later in the loop needs an explicit `else`, even when "the false case should just be empty/None."
