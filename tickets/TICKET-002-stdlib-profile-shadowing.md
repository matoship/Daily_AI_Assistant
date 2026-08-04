# TICKET-002: Stdlib `profile` module shadowed by local import

**Category:** naming collision
**Module:** `models.py`

## Symptom
An import in `models.py` — `from profile import category_options` — resolved to Python's built-in `profile` module (the deterministic profiler), not the project's `daily_assistant.profile`, and the function didn't exist there anyway.

## Root cause
Two problems stacked: the import used a bare module name instead of the package-qualified `daily_assistant.profile`, and it was in the wrong file to begin with (unused in `models.py`).

## Fix
Deleted the import; `category_options` is only needed in `triage.py`, imported there as `daily_assistant.profile`.

## Lesson
This is why the project imports the installed package name everywhere (`from daily_assistant.x import y`), never bare module names — a bare name can silently collide with a stdlib module of the same name, and the failure mode isn't always a crash; sometimes it's "imports something that exists but isn't what you meant."
