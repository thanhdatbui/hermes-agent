from __future__ import annotations

import re
from pathlib import Path

import yaml


SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "research"
    / "kanban-multi-worker-research-swarm"
)


def _source() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def test_skill_frontmatter_and_description() -> None:
    match = re.search(r"^---\n(.*?)\n---", _source(), re.DOTALL)
    assert match
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter == {
        "name": "kanban-multi-worker-research-swarm",
        "description": "Coordinate parallel researchers into audited synthesis.",
    }
    assert len(frontmatter["description"]) <= 60


def test_skill_sections_are_ordered_and_complete() -> None:
    headings = re.findall(r"^## (.+)$", _source(), re.MULTILINE)
    assert headings == [
        "When to Use",
        "Prerequisites",
        "How to Run",
        "Quick Reference",
        "Procedure",
        "Pitfalls",
        "Verification",
    ]


def test_skill_requires_bounded_independent_evidence_lanes() -> None:
    src = _source()
    for token in (
        "workflow_template_id",
        "current_step_key",
        "kanban_create",
        "kanban_link",
        "kanban_comment",
        "kanban_complete",
        "kanban_block",
        "claim IDs",
        "source-diversity",
        "challenger",
        "counterevidence",
        "final auditor",
    ):
        assert token in src
    assert "bounded worker count" in src
    assert "budget ceiling" in src


def test_skill_prevents_false_consensus_and_unbounded_fanout() -> None:
    src = _source().lower()
    assert "several workers citing one source" in src
    assert "do not create workers indefinitely" in src
    assert "do not average incompatible claims" in src
    assert "do not create a second swarm engine" in src
    assert "todo" not in src
