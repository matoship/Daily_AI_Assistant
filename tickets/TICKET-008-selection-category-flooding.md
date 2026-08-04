# TICKET-008: Flat sort-and-slice let one category flood the digest

**Category:** design flaw
**Module:** `selection.py`

## Symptom
The very first real end-to-end digest had 4 out of 4 items in the "engineering" category — none of the immigration/migration articles made it in, despite real migration news existing in that run.

## Root cause
`select_for_synthesis` filtered by relevance threshold, sorted *all* surviving articles together by relevance, and took the top N. A single prolific, high-relevance-scoring source (MarkTechPost) could occupy every slot, crowding out lower-volume but still-relevant categories.

## Fix
Grouped articles by `category` first, ranked within each group, and applied `top_n_per_category` per group instead of globally — so no category can be fully excluded by another category's volume.

## Lesson
An LLM ranking articles by relevance alone doesn't guarantee balanced coverage across the topics a user actually cares about — volume in one topic can mathematically dominate a flat top-N cut. Fairness-by-category was a deliberate design decision, not something the ranking model provides for free.
