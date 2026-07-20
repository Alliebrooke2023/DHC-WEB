---
name: code-review
description: Review code changes for correctness bugs, edge cases, and clarity issues.
---

Review the code the user points you at (a file, directory, or `git diff` via
run_shell). Report findings ranked by severity:

1. **Correctness** — real bugs: wrong logic, unhandled edge cases (empty
   input, None, unicode, concurrency), resource leaks, error paths that
   swallow failures. For each, give a concrete failing scenario.
2. **Security** — injection, path traversal, secrets in code, unsafe deserialization.
3. **Clarity** — misleading names, dead code, needless complexity.

Rules:
- Read the actual code with read_file/grep before claiming anything.
- No style nitpicks a formatter would catch.
- If the code is fine, say so briefly — do not invent findings.
- End with a one-line verdict: ship it / fix first / needs rework.
