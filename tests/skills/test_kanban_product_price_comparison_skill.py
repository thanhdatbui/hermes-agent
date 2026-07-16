from __future__ import annotations

import re
from pathlib import Path

import yaml


SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "research"
    / "kanban-product-price-comparison-vn"
)


def _source() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def test_skill_frontmatter_and_description() -> None:
    match = re.search(r"^---\n(.*?)\n---", _source(), re.DOTALL)
    assert match
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter == {
        "name": "kanban-product-price-comparison-vn",
        "description": "Compare products and landed costs across Vietnam and China.",
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


def test_skill_preserves_comparison_evidence_contract() -> None:
    src = _source()
    for token in (
        "workflow_template_id",
        "current_step_key",
        "kanban_create",
        "kanban_link",
        "kanban_comment",
        "kanban_complete",
        "kanban_block",
        "landed cost",
        "exchange-rate source",
        "confidence",
        "reviewer",
        "final auditor",
    ):
        assert token in src


def test_skill_blocks_unauthorized_purchase_and_fake_certainty() -> None:
    src = _source().lower()
    assert "do not place orders" in src
    assert "do not contact sellers" in src
    assert "never represent an estimate as a guaranteed final price" in src
    assert "do not create a second research database" in src
    assert "todo" not in src
