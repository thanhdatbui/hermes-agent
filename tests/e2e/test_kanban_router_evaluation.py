"""Deterministic evaluation matrix for role routing and bounded retries."""

from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb


@pytest.fixture
def board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


@pytest.mark.parametrize(
    ("role", "expected_profile", "expected_model"),
    [
        ("planner", "expert", "reasoning"),
        ("worker", "cheap", "economy"),
        ("auditor", "audit", None),
    ],
)
def test_role_router_evaluation_matrix(board, role, expected_profile, expected_model) -> None:
    config = {"orchestration": {"roles": {
        "planner": {"candidates": [{"profile": "expert", "model": "reasoning"}]},
        "worker": {"candidates": [{"profile": "cheap", "model": "economy"}]},
        "auditor": {"candidates": ["audit"]},
    }}}
    with kb.connect() as conn:
        task_id = kb.create_task(conn, title=role, current_step_key=role)
        task = kb.get_task(conn, task_id)
    policy = kb.resolve_workflow_step_policy(task, config)
    assert policy is not None
    assert (policy.profile, policy.model) == (expected_profile, expected_model)


def test_provider_failure_switches_but_task_failure_stays_on_worker(board, monkeypatch) -> None:
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {"kanban": {"orchestration": {"roles": {
        "worker": {"candidates": ["worker-a", "worker-b"]},
    }}}})
    with kb.connect() as conn:
        provider_task = kb.create_task(conn, title="provider", assignee="worker-a", current_step_key="worker")
        with kb.write_txn(conn):
            kb._synthesize_ended_run(conn, provider_task, outcome="rate_limited")
        provider = kb.record_worker_failure_classification(
            conn, provider_task, failure_class="provider_failure", error_signature="429",
        )

        task_task = kb.create_task(conn, title="task", assignee="worker-a", current_step_key="worker", max_retries=2)
        with kb.write_txn(conn):
            kb._synthesize_ended_run(conn, task_task, outcome="failed")
        task = kb.record_worker_failure_classification(
            conn, task_task, failure_class="task_failure", error_signature="pytest",
            hypothesis="first", action_summary="changed code",
        )

    assert provider["switched"] is True and provider["next_profile"] == "worker-b"
    assert task["switched"] is False and task["meaningful"] is True
