from __future__ import annotations

import re
from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "autonomous-ai-agents" / "kanban-codex-lane"


def _source() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def test_skill_frontmatter_and_description() -> None:
    match = re.search(r"^---\n(.*?)\n---", _source(), re.DOTALL)
    assert match
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter == {
        "name": "kanban-codex-lane",
        "description": "Run bounded Codex implementation lanes through Kanban.",
    }
    assert len(frontmatter["description"]) <= 60


def test_skill_sections_are_ordered_and_complete() -> None:
    assert re.findall(r"^## (.+)$", _source(), re.MULTILINE) == [
        "When to Use", "Prerequisites", "How to Run", "Quick Reference",
        "Procedure", "Pitfalls", "Verification",
    ]


def test_skill_uses_native_kanban_tools_and_worktrees() -> None:
    src = _source()
    for token in (
        "kanban_show", "kanban_comment", "kanban_complete.metadata.codex_lane",
        "kanban_block", "kanban_codex_lane", "process_registry", "worktree",
    ):
        assert token in src


def test_skill_blocks_destructive_actions() -> None:
    src = _source().lower()
    assert "--yolo" in src
    assert "do not use `--yolo`" in src
    assert "edge-plugin\n   auto-commit" in src
    assert "codex output alone is never authoritative" in src


def test_skill_resolves_accepted_diff_before_retry() -> None:
    src = _source().lower()
    assert "accepted patch is applied" in src
    assert "uncommitted diff" in src
    assert "never relaunch the lane while that workspace is dirty" in src
    assert "resolve the existing\n   diff instead of retrying" in src
    assert "source workspace at the starting `head` and clean" in src
    assert "inspect the durable patch artifact instead of merging two timelines" in src
    assert "for a rename, review both the old and new path" in src
    assert "stages a snapshot only after those tests finish" in src
