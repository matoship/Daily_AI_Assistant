# TICKET-039: `--tool-call-parser` was silently ignored, and the error asked for the flag already passed

**Category:** CI/config / misleading diagnostic
**Module:** vLLM serve command (`vllm serve`, vLLM 0.29.0)

## Symptom
The first live evaluation against the local server failed on its first article with a 400:

```
tool_choice=function "provide_triage_result" requires --tool-call-parser to be set
```

After restarting with `--tool-call-parser hermes`, the same request returned the same error.
`ps` confirmed the running process carried the flag.

## Root cause
In vLLM 0.29.0, `ParserManager.get_tool_parser` returns `None` unless auto tool choice is
enabled, regardless of the parser name:

```python
if not enable_auto_tools or tool_parser_name is None:
    return parser          # None
```

Without `--enable-auto-tool-choice`, the parser named by `--tool-call-parser` is never
loaded. The request validator in `online_renderer.py` then checks only whether a parser
*object* exists, finds none, and reports that the *flag* is missing. This happens for a
named `tool_choice` too, even though that path never uses "auto" selection.

The flag's name and documentation suggest it matters only for `tool_choice="auto"`. That
was the wrong mental model, and retrying with variations of the flag could not have
corrected it.

## Fix
Serve with both flags:

```
vllm serve Qwen/Qwen3-4B-Instruct-2507 ... --enable-auto-tool-choice --tool-call-parser hermes
```

A minimal forced-tool-call `curl` now returns a populated `tool_calls` array.

## Lesson
**An error message reports what the check tested, not what the user did wrong.** The check
was "is there a parser object?", not "was the flag passed?". When an error tells you to do
something you have already done, stop retrying and read the code that raised it. Here the
installed package source settled the question in two greps.

**The error taxonomy behaved as designed.** The 400 became `BadRequestError`, which became
`LLMConfigurationError`, and the run stopped on the first article instead of logging the
same failure fifty times (`TICKET-037`).
