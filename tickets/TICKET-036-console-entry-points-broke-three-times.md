# TICKET-036: Console entry points broke three times on signature changes

**Category:** CI/config + test coverage gap
**Module:** `run.py`, `eval/sanity.py`, `eval/report.py`

## Symptom
Three separate breakages of installed commands, each with a fully green test suite:

- `daily-assistant-sanity` → `TypeError: triage_article() missing 1 required positional argument: 'model'`
- `daily-assistant` → `TypeError: 'bool' object is not iterable`
- `daily-assistant-report` → `TypeError: main() missing 1 required positional argument: 'argv'`

The first two would have failed the nightly CI run. All three were found by running the
command, not by the suite.

## Root cause
Console scripts declared in `[project.scripts]` are invoked by a generated launcher that
calls the registered function **with no arguments**. Nothing in the test suite went through
that path — every test called the underlying functions directly, with arguments — so
`main`'s signature had no test surface at all.

The second break also had a specific trigger: a `--vllm` flag was added by giving `main` a
`local: bool = False` parameter and passing it to `parser.parse_args()`, which expects a
list of strings or `None`.

The third was *induced by silencing a type checker*. mypy reported an incompatible default
(`None` for a parameter annotated `list[str]`). The default was deleted to make the message
go away, which satisfied mypy and broke the launcher. The annotation was what was wrong.

## Fix
`tests/test_entry_points.py` reads `[project.scripts]` from `pyproject.toml`, imports each
registered target, and asserts it can be bound with no arguments. Reading the table from
configuration means a newly added command is covered without anyone remembering to.

## Lesson
**The code that calls your program in production may be code you did not write.** A
console-script launcher, a cron line, a workflow step: each is an untested caller with its
own calling convention. At least one test should enter through the same door the user does.

**When a type checker complains about a default, the annotation is usually what is wrong.**
Removing the default silences the message by breaking the program; widening the type fixes
what the checker was actually pointing at.

**This invariant is necessary, not sufficient.** `daily-assistant-sanity --help` satisfies
it and still misbehaves: the module parses no arguments at all, so `--help` falls through to
the live, paid sanity check instead of printing usage. Proving `main()` is callable is not
proving it handles its arguments.
