@AGENTS.md

## Naming: plain English for people

The repo owner reads commit history, branch names and pull requests, and
wants each one to make sense without opening it. Name things so someone who
isn't a developer can tell what they are.

- **Commit and pull request titles**: say what changes for a person using the
  app, in plain words. Write "Stop the Agent's search from reading files
  outside its folder", not "Fix glob traversal in grep". Keep technical detail
  for the body.
- **Branches**: when you create one, name it after what it does, like
  `claude/fix-notes-tag-display`. Don't add random suffixes.
- **Talking about changes**: refer to a commit or pull request by what it does
  ("the file-safety fix"), never by its ID or hash alone. If an ID is needed,
  put the plain name first.
- **Milestones**: when a notable change lands on `main`, suggest tagging it
  with a plain name, like `agent-file-safety-fix`.
- **New files and folders**: name them after what they hold. Code files follow
  the naming already used in their folder.
