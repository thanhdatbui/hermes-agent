from __future__ import annotations

import re
from pathlib import Path

import yaml


SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "research"
    / "kanban-repository-research"
)


def _source() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def test_skill_frontmatter_and_description() -> None:
    src = _source()
    match = re.search(r"^---\n(.*?)\n---", src, re.DOTALL)
    assert match
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter == {
        "name": "kanban-repository-research",
        "description": "Research repositories through durable Kanban roles.",
    }
    assert len(frontmatter["description"]) <= 60


def test_skill_sections_are_ordered_and_complete() -> None:
    src = _source()
    headings = re.findall(r"^## (.+)$", src, re.MULTILINE)
    assert headings == [
        "When to Use",
        "Prerequisites",
        "How to Run",
        "Quick Reference",
        "Procedure",
        "Pitfalls",
        "Verification",
    ]


def test_skill_uses_durable_roles_and_native_kanban_tools() -> None:
    src = _source()
    for token in (
        "workflow_template_id",
        "current_step_key",
        "kanban_create",
        "kanban_link",
        "kanban_comment",
        "kanban_complete",
        "kanban_block",
        "reviewer",
        "final auditor",
    ):
        assert token in src


def test_skill_enforces_read_only_research() -> None:
    src = _source().lower()
    assert "read-only" in src
    assert "do not edit files" in src
    assert "do not modify the repository" in src
    assert "todo" not in src
    assert "[todo" not in src
