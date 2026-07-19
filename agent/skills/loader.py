"""Skills: packaged instructions loaded from markdown.

A skill is a directory containing SKILL.md with simple frontmatter:

    ---
    name: code-review
    description: Review a diff for bugs and style issues.
    ---
    (instructions the model follows when the skill is invoked)

Skills are discovered from the project's skills/ dirs (configurable) and
from ~/.agent/skills/. Invoking a skill (/skill name, or automatically by
description match) injects its instructions into the conversation for
that turn. New capabilities are added by writing markdown, not code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    instructions: str
    path: Path


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    try:
        _, fm, body = text.split("---", 2)
    except ValueError:
        return {}, text
    meta = {}
    for line in fm.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    return meta, body.strip()


def load_skills(config) -> dict[str, Skill]:
    roots = [config.workdir / d for d in config.skills_dirs]
    roots.append(config.user_dir / "skills")

    skills: dict[str, Skill] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            meta, body = _parse_frontmatter(skill_md.read_text())
            name = meta.get("name", skill_md.parent.name)
            skills[name] = Skill(
                name=name,
                description=meta.get("description", ""),
                instructions=body,
                path=skill_md,
            )
    return skills
