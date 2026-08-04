# TICKET-020: Three YAML authoring errors in the Actions workflow

**Category:** CI/config
**Module:** `.github/workflows/daily-digest.yaml`

## Symptom
Caught in review before the first run, not from a failed run: three separate mistakes in the first draft of the workflow file.

## Root cause
1. `permissions: contents: write` was indented as a nested child of `on:` instead of a top-level sibling key — YAML structure *is* semantics, so this would have been parsed as part of the trigger config, leaving the job's token read-only and the final `git push` step likely to fail with a 403.
2. A shell command (`printf '%s' "$PROFILE_YAML" > ...`) was written under a `uses:` key instead of `run:` — `uses:` tells Actions to resolve a marketplace action by that name, so it would have tried (and failed) to find an action literally named `printf '%s' ...`.
3. `git add doc seen.db` — a typo dropping the `s` from `docs` — which would have caused git to error on that path and, depending on script structure, potentially skip committing the actual digest output entirely.

## Fix
Dedented `permissions` to top level; changed `uses:` to `run:` for the shell step; corrected `doc` to `docs`.

## Lesson
CI workflow files fail differently from application code: a YAML structure mistake or a wrong-key mistake often doesn't announce itself clearly, and a `git add` typo can fail in a way that silently drops the very thing the job exists to produce. Reviewing a workflow file line-by-line against what each key actually means (trigger vs. permissions vs. step type) before the first live run is cheaper than debugging it after a real scheduled failure.
