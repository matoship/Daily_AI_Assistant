# TICKET-012: Outdated-sweep had no status filter, could demote delivered items

**Category:** design flaw
**Module:** `storage.py`

## Symptom
An early draft of `mark_outdated_before` would flip *any* article older than the cutoff to `outdated` — including articles already marked `digested` (i.e., actually delivered to the user) or `scored` (already triaged and rejected).

## Root cause
The sweep was designed around "how old is this row," treating `outdated` as an age label. But `status` should record an *outcome* (what happened to the article), not a derivable fact like age — `first_seen_at` already answers "how old." Overwriting `digested` with `outdated` would erase the historical record that an article was ever delivered.

## Fix
Restricted the sweep to `WHERE status = 'fetched'` only — the one status that represents "still in limbo." `digested` and `scored` are terminal outcomes and are never touched by the sweep.

## Lesson
A status column should record what happened (a fact with no other source of truth), not something derivable on demand from other columns (like age from a timestamp). Terminal states — states nothing should ever transition *out of* — deserve that guarantee to be enforced explicitly in every mutation, not left as an implicit assumption.
