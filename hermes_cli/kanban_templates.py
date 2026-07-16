"""Config-backed workflow template registry derived from shipped skills."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from hermes_cli.config import load_config


_TEMPLATE_RE = re.compile(r"workflow_template_id\s*=\s*[\"']([^\"']+)[\"']")
_STEP_RE = re.compile(r"current_step_key\s*=\s*[\"']([^\"']+)[\"']")


@dataclass(frozen=True)
class WorkflowTemplate:
    id: str
    name: str
    description: str
    skill: str | None = None
    roles: tuple[str, ...] = ()
    source: str = "bundled"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["roles"] = list(self.roles)
        return data


def _skill_roots() -> tuple[Path, ...]:
    repo = Path(__file__).resolve().parent.parent
    return (repo / "skills", repo / "optional-skills")


def _frontmatter(source: str) -> dict[str, Any]:
    if not source.startswith("---\n"):
        return {}
    end = source.find("\n---", 4)
    if end < 0:
        return {}
    parsed = yaml.safe_load(source[4:end]) or {}
    return parsed if isinstance(parsed, dict) else {}


def discover_bundled_templates(roots: Iterable[Path] | None = None) -> list[WorkflowTemplate]:
    found: dict[str, WorkflowTemplate] = {}
    for root in roots or _skill_roots():
        if not root.exists():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            source = path.read_text(encoding="utf-8")
            ids = sorted(set(_TEMPLATE_RE.findall(source)))
            if not ids:
                continue
            meta = _frontmatter(source)
            skill_name = str(meta.get("name") or path.parent.name)
            description = str(meta.get("description") or "").strip()
            roles = tuple(sorted(set(_STEP_RE.findall(source))))
            for template_id in ids:
                found.setdefault(template_id, WorkflowTemplate(
                    id=template_id,
                    name=skill_name.replace("-", " ").title(),
                    description=description,
                    skill=skill_name,
                    roles=roles,
                ))
    return sorted(found.values(), key=lambda item: item.id)


def list_workflow_templates(config: dict[str, Any] | None = None,
                            roots: Iterable[Path] | None = None) -> list[WorkflowTemplate]:
    templates = {item.id: item for item in discover_bundled_templates(roots)}
    cfg = config if config is not None else load_config()
    custom = ((cfg or {}).get("kanban") or {}).get("workflow_templates") or {}
    if not isinstance(custom, dict):
        raise ValueError("kanban.workflow_templates must be a mapping")
    for template_id, raw in custom.items():
        if not isinstance(raw, dict):
            raise ValueError(f"kanban.workflow_templates.{template_id} must be a mapping")
        roles = raw.get("roles") or []
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise ValueError(f"kanban.workflow_templates.{template_id}.roles must be a string list")
        templates[str(template_id)] = WorkflowTemplate(
            id=str(template_id),
            name=str(raw.get("name") or template_id),
            description=str(raw.get("description") or ""),
            skill=str(raw.get("skill") or "") or None,
            roles=tuple(roles),
            source="config",
        )
    return sorted(templates.values(), key=lambda item: item.id)


def get_workflow_template(template_id: str, **kwargs: Any) -> WorkflowTemplate | None:
    return next((item for item in list_workflow_templates(**kwargs) if item.id == template_id), None)
