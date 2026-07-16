from __future__ import annotations

import re
from pathlib import Path

import yaml


SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "research"
    / "kanban-document-analysis-report"
)


def _source() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def test_skill_frontmatter_and_description() -> None:
    match = re.search(r"^---\n(.*?)\n---", _source(), re.DOTALL)
    assert match
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter == {
        "name": "kanban-document-analysis-report",
        "description": "Analyze documents and produce auditable reports.",
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


def test_skill_requires_traceable_document_evidence() -> None:
    src = _source()
    for token in (
        "workflow_template_id",
        "current_step_key",
        "kanban_create",
        "kanban_link",
        "kanban_comment",
        "kanban_complete",
        "kanban_block",
        "page/section/table citations",
        "OCR",
        "confidence",
        "contradictions",
        "final auditor",
    ):
        assert token in src


def test_skill_preserves_sources_and_confidentiality() -> None:
    src = _source().lower()
    assert "do not alter source documents" in src
    assert "do not expose confidential document contents" in src
    assert "do not create a second document database" in src
    assert "missing attachments" in src
    assert "todo" not in src
