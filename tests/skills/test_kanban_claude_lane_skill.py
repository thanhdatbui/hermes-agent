from __future__ import annotations

import re
from pathlib import Path

import yaml


SKILL = Path(__file__).resolve().parents[2] / "skills" / "autonomous-ai-agents" / "kanban-claude-lane" / "SKILL.md"


def _source() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_frontmatter_and_description() -> None:
    match = re.search(r"^---\n(.*?)\n---", _source(), re.DOTALL)
    assert match
    data = yaml.safe_load(match.group(1))
    assert data["name"] == "kanban-claude-lane"
    assert len(data["description"]) <= 60


def test_sections_follow_skill_standard() -> None:
    assert re.findall(r"^## (.+)$", _source(), re.MULTILINE) == [
        "When to Use", "Prerequisites", "How to Run", "Quick Reference",
        "Procedure", "Pitfalls", "Verification",
    ]


def test_skill_uses_kanban_and_structured_evidence() -> None:
    src = _source()
    for token in ("kanban_show", "kanban_claude_lane", "process_registry", "kanban_complete.metadata.claude_lane", "usage", "cost"):
        assert token in src


def test_skill_blocks_permission_bypass_and_partial_acceptance() -> None:
    src = _source().lower()
    assert "--dangerously-skip-permissions" in src
    assert "permission-mode bypasspermissions" in src
    assert "do not allow partial acceptance" in src


def test_skill_resolves_accepted_diff_before_retry() -> None:
    src = _source().lower()
    assert "accepted patch is applied" in src
    assert "uncommitted diff" in src
    assert "never relaunch the lane while that workspace is dirty" in src
    assert "resolve the existing\n   diff instead of retrying" in src
    assert "source workspace at the starting `head` and clean" in src
    assert "inspect the durable patch artifact instead of merging two timelines" in src
    assert "for a rename, review both the old and new path" in src
    assert "stages a snapshot only after tests finish" in src
