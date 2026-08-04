# TICKET-011: `INSERT OR REPLACE` silently nulled `first_seen_at`

**Category:** silent data bug
**Module:** `storage.py`

## Symptom
Every row's `first_seen_at` column was `NULL`, even though it was supposed to be set once, on first insert, and preserved on every later status update.

## Root cause
`upsert_status` used `INSERT OR REPLACE`, which — contrary to its name — doesn't merge fields into an existing row. On conflict, it deletes the entire old row and inserts a brand-new one containing only the columns explicitly listed in the statement. `first_seen_at` was never included in that statement, so every "update" silently wiped it back to its default.

## Fix
Switched to `INSERT ... ON CONFLICT(url) DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at` — which updates only the named columns and leaves `first_seen_at` untouched on conflict.

## Lesson
`INSERT OR REPLACE` is a delete-then-insert, not a merge — any column not present in the statement reverts to its column default on every update, and SQLite does this without error or warning. When you need "update these fields, but leave everything else alone," `ON CONFLICT ... DO UPDATE` is the correct tool; `OR REPLACE` almost never is once a table has more than the conflict column.
