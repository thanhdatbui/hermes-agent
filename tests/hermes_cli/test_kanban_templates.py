from pathlib import Path

import pytest

from hermes_cli.kanban_templates import get_workflow_template, list_workflow_templates


def _skill(root: Path, name: str, body: str) -> None:
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"---\nname: {name}\ndescription: Test template.\n---\n{body}", encoding="utf-8")


def test_registry_discovers_templates_and_roles(tmp_path: Path) -> None:
    _skill(tmp_path, "demo", 'workflow_template_id="demo-v1" current_step_key="worker"')
    items = list_workflow_templates(config={}, roots=[tmp_path])
    assert [item.id for item in items] == ["demo-v1"]
    assert items[0].roles == ("worker",)


def test_real_registry_contains_coding_and_non_coding_workflows() -> None:
    ids = {item.id for item in list_workflow_templates()}
    assert "kanban-orchestrated-coding" in ids
    assert "repository-research-v1" in ids
    assert "computer-use-lane-v1" in ids


def test_config_template_overrides_discovered_entry(tmp_path: Path) -> None:
    _skill(tmp_path, "demo", 'workflow_template_id="demo-v1"')
    config = {"kanban": {"workflow_templates": {"demo-v1": {"name": "Custom", "roles": ["auditor"]}}}}
    item = get_workflow_template("demo-v1", config=config, roots=[tmp_path])
    assert item is not None and item.name == "Custom" and item.source == "config"


def test_invalid_custom_roles_fail_closed() -> None:
    config = {"kanban": {"workflow_templates": {"bad": {"roles": "worker"}}}}
    with pytest.raises(ValueError, match="roles"):
        list_workflow_templates(config=config, roots=[])


def test_cli_templates_emits_machine_readable_catalog(monkeypatch, capsys) -> None:
    from argparse import Namespace
    from hermes_cli import kanban
    from hermes_cli.kanban_templates import WorkflowTemplate

    monkeypatch.setattr(
        "hermes_cli.kanban_templates.list_workflow_templates",
        lambda: [WorkflowTemplate("demo-v1", "Demo", "", "demo", ("worker",))],
    )
    assert kanban._cmd_templates(Namespace(json=True)) == 0
    assert '"id": "demo-v1"' in capsys.readouterr().out
