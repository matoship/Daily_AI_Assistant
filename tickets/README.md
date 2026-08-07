# Tickets

A postmortem log of real issues found and fixed while building this project — maintained by Claude (mentor/reviewer across the whole build), as a companion to `../notes/` (Kaifeng's own learning notes) and `../TODO.md` (open work).

Each ticket: what broke, why, how it was fixed, and the generalizable lesson. Numbered roughly in the order encountered, not by severity.

## Index

| # | Title | Category |
|---|---|---|
| [001](TICKET-001-text-completions-api-mismatch.md) | Text Completions API mismatch (`response.completion`) | mock drift |
| [002](TICKET-002-stdlib-profile-shadowing.md) | Stdlib `profile` module shadowed by local import | naming collision |
| [003](TICKET-003-topics-casing-empty-categories.md) | `Topics` vs `topics` casing silently emptied categories | silent data bug |
| [004](TICKET-004-source-py-refactor-regressions.md) | Regressions reintroduced during a source.py rewrite | regression |
| [005](TICKET-005-feed-mock-missing-attributes.md) | Feed mock used plain dict, not `FeedParserDict` | mock drift |
| [006](TICKET-006-run-py-wiring-bugs.md) | run.py wiring drifted from renamed function signatures | integration gap |
| [007](TICKET-007-synthesize-empty-selection-crash.md) | `synthesize()` crashed on an empty selection | edge case |
| [008](TICKET-008-selection-category-flooding.md) | Flat sort-and-slice let one category flood the digest | design flaw |
| [009](TICKET-009-test-couldnt-distinguish-implementations.md) | Test suite couldn't tell old and new selection logic apart | false confidence |
| [010](TICKET-010-mark-at-fetch-dropped-articles.md) | Mark-at-fetch dedup permanently dropped capped articles | design flaw |
| [011](TICKET-011-insert-or-replace-nulled-column.md) | `INSERT OR REPLACE` silently nulled `first_seen_at` | silent data bug |
| [012](TICKET-012-sweep-had-no-status-filter.md) | Outdated-sweep had no status filter, could demote delivered items | design flaw |
| [013](TICKET-013-sweep-param-order-swap.md) | SQL positional-parameter swap disabled the sweep's time window | silent data bug |
| [014](TICKET-014-dead-feeds-silent-404.md) | Dead government RSS feeds silently returned zero articles | silent failure |
| [015](TICKET-015-published-at-stale-carryover.md) | `published_at` carried a stale value across feed entries | silent data bug |
| [016](TICKET-016-non-feed-source-zero-entries.md) | A non-feed URL (TLDR homepage) silently yielded 0 entries | silent failure |
| [017](TICKET-017-cross-feed-duplicate-triage.md) | Same article from two feeds triaged twice in one run | wasted cost |
| [018](TICKET-018-unescaped-html-render.md) | Digest renderer didn't escape untrusted LLM/feed text | security |
| [019](TICKET-019-index-orphaned-archive.md) | Archive index only ever linked the current day | design flaw |
| [020](TICKET-020-ci-workflow-authoring-errors.md) | Three YAML authoring errors in the Actions workflow | CI/config |
| [021](TICKET-021-env-secret-scoping-empty-key.md) | Environment-scoped secret invisible to the job; no validation caught it | CI/config + fail-fast gap |
| [022](TICKET-022-scheduled-trigger-missed-firing.md) | Scheduled workflow trigger silently missed a daily firing | CI/config |
| [023](TICKET-023-same-day-overwrite-utc-date-mismatch.md) | Same-day reruns silently overwrote the digest; UTC date caused archive gaps | design flaw + silent data bug |
