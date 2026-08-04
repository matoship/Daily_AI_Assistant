# TICKET-018: Digest renderer didn't escape untrusted LLM/feed text

**Category:** security
**Module:** `render.py`

## Symptom
None yet observed in practice — caught in review before the page went live, not from an incident.

## Root cause
`render_digest_page` interpolated `DigestItem` fields (headline, summary, why_it_matters — all either LLM-generated or derived from external feed titles) directly into an HTML string with plain f-strings. Since this page is published publicly via GitHub Pages, any `<script>` or other HTML-significant content appearing in a feed title or slipping through an LLM response would execute in a visitor's browser — a stored XSS vector.

## Fix
Wrapped every interpolated value in `html.escape(...)` before inserting it into the page, including URLs.

## Lesson
Text originating outside your own code — user input, third-party feed content, or LLM output — is untrusted the moment it crosses into a rendering context, regardless of how it got there. This is the HTML-output equivalent of parameterized SQL: never string-interpolate untrusted content directly into a format that will be *executed or rendered*, whether that's a SQL query, a shell command, or an HTML page.
