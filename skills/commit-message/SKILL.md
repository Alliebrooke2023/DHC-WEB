---
name: commit-message
description: Write a conventional commit message for the currently staged changes.
---

Run `git diff --cached` (run_shell) to see the staged changes. If nothing is
staged, say so and stop.

Write a commit message:
- First line: conventional-commit style, imperative, <= 72 chars
  (feat:/fix:/refactor:/docs:/test:/chore:).
- Body: what changed and why, wrapped at 72 chars. Skip the body for trivial
  changes.
- Never mention files the diff does not touch.

Output only the commit message in a code block, then offer to run the commit.
