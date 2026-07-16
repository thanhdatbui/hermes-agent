"""DB-level contracts for Kanban Orchestrated Coding slice 3."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


def _events(conn: sqlite3.Connection, task_id: str, kind: str) -> list[kb.Event]:
    return [event for event in kb.list_events(conn, task_id) if event.kind == kind]


def _count_tasks_with_key(conn: sqlite3.Connection, key: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM tasks WHERE idempotency_key = ?",
        (key,),
    ).fetchone()
    return int(row["n"]) if row else 0


def test_workflow_step_policy_uses_primary_candidate_without_role_metadata(
    kanban_home,
):
    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="plan a routed change",
            workflow_template_id="kanban-orchestrated-coding",
            current_step_key="planner",
        )
        task = kb.get_task(conn, task_id)

    assert task is not None
    policy = kb.resolve_workflow_step_policy(task, {
        "orchestration": {
            "roles": {
                "planner": {
                    "candidates": [
                        {"profile": "expert-planner", "model": "reasoning-model"},
                        {"profile": "backup-planner"},
                    ],
                    "toolsets": ["skills", "file", "file"],
                },
            },
        },
    })

    assert policy is not None
    assert policy.step_key == "planner"
    assert policy.profile == "expert-planner"
    assert policy.model == "reasoning-model"
    assert policy.toolsets == ["file", "skills"]
    assert task.current_step_key == "planner"


def test_workflow_step_policy_is_inert_without_step_or_role(kanban_home):
    with kb.connect() as conn:
        task_id = kb.create_task(conn, title="ordinary existing task", assignee="legacy")
        task = kb.get_task(conn, task_id)

    assert task is not None
    assert kb.resolve_workflow_step_policy(task, {"orchestration": {"roles": {}}}) is None


def test_workflow_step_policy_rejects_malformed_candidate_config(kanban_home):
    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="bad route config",
            current_step_key="worker",
        )
        task = kb.get_task(conn, task_id)

    assert task is not None
    with pytest.raises(ValueError, match="candidates must be a non-empty list"):
        kb.resolve_workflow_step_policy(task, {
            "orchestration": {"roles": {"worker": {"candidates": []}}},
        })
    with pytest.raises(ValueError, match="duplicate profile"):
        kb.resolve_workflow_step_policy(task, {
            "orchestration": {
                "roles": {
                    "worker": {
                        "candidates": ["same-worker", {"profile": "same-worker"}],
                    },
                },
            },
        })


def test_default_spawn_pins_role_toolsets_and_primary_model(
    kanban_home, monkeypatch, tmp_path,
):
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 4242

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {
        "kanban": {
            "orchestration": {
                "roles": {
                    "worker": {
                        "candidates": [{"profile": "cheap-worker", "model": "cheap-model"}],
                        "toolsets": ["terminal", "file"],
                    },
                },
            },
        },
    })
    monkeypatch.setattr(kb, "_resolve_hermes_argv", lambda: ["hermes"])
    monkeypatch.setattr("subprocess.Popen", fake_popen)

    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="execute routed change",
            assignee="legacy-worker",
            current_step_key="worker",
        )
        task = kb.get_task(conn, task_id)

    assert task is not None
    assert kb._default_spawn(task, str(tmp_path)) == 4242
    cmd = captured["cmd"]
    assert cmd[cmd.index("-p") + 1] == "cheap-worker"
    assert cmd[cmd.index("-m") + 1] == "cheap-model"
    assert cmd[cmd.index("--toolsets") + 1] == "file,terminal"


def test_dispatcher_persists_step_primary_lane_before_claim(
    kanban_home, monkeypatch,
):
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {
        "kanban": {
            "orchestration": {
                "roles": {
                    "worker": {
                        "candidates": [{"profile": "cheap-worker", "model": "cheap-model"}],
                        "toolsets": ["terminal", "file"],
                    },
                },
            },
        },
    })
    monkeypatch.setattr("hermes_cli.profiles.profile_exists", lambda _name: True)

    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="dispatch with role route",
            assignee="legacy-worker",
            current_step_key="worker",
        )
        result = kb._dispatch_once_locked(
            conn,
            spawn_fn=lambda _task, _workspace: 4242,
            max_spawn=1,
        )
        task = kb.get_task(conn, task_id)
        runs = kb.list_runs(conn, task_id)
        routed = _events(conn, task_id, "workflow_step_routed")

    assert result.spawned and result.spawned[0][0] == task_id
    assert task is not None
    assert task.assignee == "cheap-worker"
    assert task.model_override == "cheap-model"
    assert runs[-1].profile == "cheap-worker"
    assert runs[-1].step_key == "worker"
    assert routed[-1].payload == {
        "step_key": "worker",
        "profile": "cheap-worker",
        "model": "cheap-model",
    }


def _install_worker_candidates(monkeypatch, candidates):
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {
        "kanban": {
            "orchestration": {
                "roles": {
                    "worker": {
                        "candidates": candidates,
                        "toolsets": ["terminal", "file"],
                    },
                },
            },
        },
    })


def test_provider_failure_switches_candidate_and_resets_failure_counter(
    kanban_home, monkeypatch,
):
    _install_worker_candidates(monkeypatch, [
        {"profile": "worker-a", "model": "model-a"},
        {"profile": "worker-b", "model": "model-b"},
    ])
    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="switch provider lane",
            assignee="worker-a",
            current_step_key="worker",
        )
        with kb.write_txn(conn):
            conn.execute(
                "UPDATE tasks SET consecutive_failures = 2 WHERE id = ?",
                (task_id,),
            )
            kb._synthesize_ended_run(
                conn, task_id, outcome="rate_limited", error="429 quota wall",
            )

        result = kb.record_worker_failure_classification(
            conn,
            task_id,
            failure_class="provider_failure",
            error_signature="http_429_rate_limit",
            artifact_refs=["logs/worker-a.log"],
        )
        task = kb.get_task(conn, task_id)
        run = kb.list_runs(conn, task_id)[-1]
        guard = kb.check_respawn_guard(conn, task_id)

    assert result["switched"] is True
    assert result["next_profile"] == "worker-b"
    assert task is not None
    assert task.assignee == "worker-b"
    assert task.model_override == "model-b"
    assert task.consecutive_failures == 0
    assert guard is None
    assert run.metadata["failure_class"] == "provider_failure"
    assert run.metadata["error_signature"] == "http_429_rate_limit"
    assert run.metadata["artifact_refs"] == ["logs/worker-a.log"]


def test_rate_limit_exit_uses_provider_failure_candidate_policy(
    kanban_home, monkeypatch,
):
    _install_worker_candidates(monkeypatch, ["worker-a", "worker-b"])
    monkeypatch.setattr(kb, "_pid_alive", lambda _pid: False)
    monkeypatch.setattr(kb, "_classify_worker_exit", lambda _pid: ("rate_limited", 75))
    monkeypatch.setattr(kb, "_resolve_crash_grace_seconds", lambda: 0)

    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="rate limit integration",
            assignee="worker-a",
            current_step_key="worker",
        )
        claimed = kb.claim_task(conn, task_id)
        assert claimed is not None
        with kb.write_txn(conn):
            conn.execute(
                "UPDATE tasks SET worker_pid = 4242, started_at = 1 WHERE id = ?",
                (task_id,),
            )
        crashed = kb.detect_crashed_workers(conn)
        task = kb.get_task(conn, task_id)
        run = kb.list_runs(conn, task_id)[-1]

    assert crashed == []
    assert task is not None
    assert task.status == "ready"
    assert task.assignee == "worker-b"
    assert task.consecutive_failures == 0
    assert run.outcome == "rate_limited"
    assert run.metadata["failure_class"] == "provider_failure"
    assert run.metadata["error_signature"] == "provider_rate_limited"


def test_task_failure_does_not_switch_candidate_and_consumes_retry(
    kanban_home, monkeypatch,
):
    _install_worker_candidates(monkeypatch, ["worker-a", "worker-b"])
    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="failed acceptance test",
            assignee="worker-a",
            current_step_key="worker",
            max_retries=3,
        )
        with kb.write_txn(conn):
            kb._synthesize_ended_run(
                conn, task_id, outcome="failed", error="pytest failed",
            )
        result = kb.record_worker_failure_classification(
            conn,
            task_id,
            failure_class="task_failure",
            error_signature="pytest:test_add",
            hypothesis="off-by-one",
            action_summary="changed loop bound",
            changed_files=["math_bug.py"],
            test_result={"exit_code": 1},
        )
        task = kb.get_task(conn, task_id)
        run = kb.list_runs(conn, task_id)[-1]

    assert result["switched"] is False
    assert result["meaningful"] is True
    assert task is not None
    assert task.assignee == "worker-a"
    assert task.consecutive_failures == 1
    assert run.step_key == "worker"
    assert "step_key" not in run.metadata
    assert "role" not in run.metadata


def test_repeated_identical_task_failure_evidence_does_not_consume_retry(
    kanban_home, monkeypatch,
):
    _install_worker_candidates(monkeypatch, ["worker-a", "worker-b"])
    evidence = {
        "failure_class": "task_failure",
        "error_signature": "pytest:test_add",
        "hypothesis": "off-by-one",
        "action_summary": "changed loop bound",
    }
    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="dedupe failed attempt",
            assignee="worker-a",
            current_step_key="worker",
            max_retries=3,
        )
        with kb.write_txn(conn):
            kb._synthesize_ended_run(conn, task_id, outcome="failed")
        first = kb.record_worker_failure_classification(conn, task_id, **evidence)
        with kb.write_txn(conn):
            kb._synthesize_ended_run(conn, task_id, outcome="failed")
        replay = kb.record_worker_failure_classification(conn, task_id, **evidence)
        task = kb.get_task(conn, task_id)

    assert first["meaningful"] is True
    assert replay["meaningful"] is False
    assert task is not None
    assert task.consecutive_failures == 1


def test_provider_candidate_switching_is_bounded_then_uses_failure_limit(
    kanban_home, monkeypatch,
):
    _install_worker_candidates(monkeypatch, ["worker-a", "worker-b"])
    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="bounded provider candidates",
            assignee="worker-a",
            current_step_key="worker",
        )
        with kb.write_txn(conn):
            kb._synthesize_ended_run(conn, task_id, outcome="rate_limited")
        switched = kb.record_worker_failure_classification(
            conn,
            task_id,
            failure_class="provider_failure",
            error_signature="provider_unavailable",
            failure_limit=2,
        )
        with kb.write_txn(conn):
            kb._synthesize_ended_run(conn, task_id, outcome="rate_limited")
        exhausted_once = kb.record_worker_failure_classification(
            conn,
            task_id,
            failure_class="provider_failure",
            error_signature="provider_unavailable",
            failure_limit=2,
        )
        with kb.write_txn(conn):
            kb._synthesize_ended_run(conn, task_id, outcome="rate_limited")
        exhausted_twice = kb.record_worker_failure_classification(
            conn,
            task_id,
            failure_class="provider_failure",
            error_signature="provider_unavailable",
            failure_limit=2,
        )
        task = kb.get_task(conn, task_id)
        switched_events = _events(conn, task_id, "worker_candidate_switched")

    assert switched["next_profile"] == "worker-b"
    assert exhausted_once["candidate_exhausted"] is True
    assert exhausted_once["blocked"] is False
    assert exhausted_twice["blocked"] is True
    assert task is not None
    assert task.assignee == "worker-b"
    assert task.status == "blocked"
    assert len(switched_events) == 1


def test_verdict_on_auditor_task_id_does_not_open_executor_gate(kanban_home):
    with kb.connect() as conn:
        executor = kb.create_task(
            conn,
            title="execute guarded change",
            assignee="executor",
            plan_audit_required=True,
        )
        auditor = kb.create_task(
            conn,
            title="audit executor plan",
            assignee="plan-auditor",
        )

        kb.record_plan_audit_verdict(
            conn,
            auditor,
            approved=True,
            reviewer="plan-auditor",
            reason="recorded on the wrong task id",
        )
        wrong_claim = kb.claim_task(conn, executor, claimer="executor")
        executor_after_wrong_id = kb.get_task(conn, executor)

        kb.record_plan_audit_verdict(
            conn,
            executor,
            approved=True,
            reviewer="plan-auditor",
            reason="recorded on the gated executor task id",
        )
        right_claim = kb.claim_task(conn, executor, claimer="executor")
        executor_after_right_id = kb.get_task(conn, executor)

    assert wrong_claim is None
    assert executor_after_wrong_id is not None
    assert executor_after_wrong_id.status == "ready"
    assert right_claim is not None
    assert executor_after_right_id is not None
    assert executor_after_right_id.status == "running"


def test_ready_executor_still_cannot_claim_before_plan_approval(kanban_home):
    with kb.connect() as conn:
        planner = kb.create_task(conn, title="write initial plan", assignee="planner")
        executor = kb.create_task(
            conn,
            title="execute after plan",
            assignee="executor",
            parents=(planner,),
            plan_audit_required=True,
        )
        assert kb.get_task(conn, executor).status == "todo"

        assert kb.complete_task(conn, planner, summary="initial plan written")
        promoted = kb.get_task(conn, executor)
        assert promoted is not None
        assert promoted.status == "ready"

        claimed = kb.claim_task(conn, executor, claimer="executor")
        after_claim_attempt = kb.get_task(conn, executor)
        requested = _events(conn, executor, "plan_audit_requested")

    assert claimed is None
    assert after_claim_attempt is not None
    assert after_claim_attempt.status == "ready"
    assert len(requested) == 1
    assert requested[-1].payload == {"rejected_rounds": 0, "limit": 2}


def test_replayed_rejected_round_is_idempotent_and_does_not_exhaust_early(
    kanban_home,
):
    with kb.connect() as conn:
        executor = kb.create_task(
            conn,
            title="executor with retry-safe audit",
            assignee="executor",
            plan_audit_required=True,
            plan_audit_max_rounds=2,
        )
        metadata = {"round": 1, "kind": "revise_plan"}

        kb.record_plan_audit_verdict(
            conn,
            executor,
            approved=False,
            reviewer="plan-auditor",
            reason="missing files",
            metadata=metadata,
        )
        kb.record_plan_audit_verdict(
            conn,
            executor,
            approved=False,
            reviewer="plan-auditor",
            reason="missing files",
            metadata=metadata,
        )

        claimed = kb.claim_task(conn, executor, claimer="executor")
        task = kb.get_task(conn, executor)
        rejected_events = _events(conn, executor, "plan_audit_rejected")
        requested_events = _events(conn, executor, "plan_audit_requested")

    assert len(rejected_events) == 1
    assert claimed is None
    assert task is not None
    assert task.status == "ready"
    assert task.block_kind is None
    assert requested_events[-1].payload == {"rejected_rounds": 1, "limit": 2}


def test_legacy_duplicate_rejected_events_with_same_round_do_not_exhaust_early(
    kanban_home,
):
    with kb.connect() as conn:
        executor = kb.create_task(
            conn,
            title="executor with historical duplicate audit event",
            assignee="executor",
            plan_audit_required=True,
            plan_audit_max_rounds=2,
        )
        payload = json.dumps({
            "reason": "legacy replay duplicate",
            "metadata": {"round": 1, "kind": "revise_plan"},
        })
        now = int(time.time())
        with kb.write_txn(conn):
            conn.execute(
                "INSERT INTO task_events (task_id, kind, payload, created_at) "
                "VALUES (?, 'plan_audit_rejected', ?, ?)",
                (executor, payload, now),
            )
            conn.execute(
                "INSERT INTO task_events (task_id, kind, payload, created_at) "
                "VALUES (?, 'plan_audit_rejected', ?, ?)",
                (executor, payload, now),
            )

        claimed = kb.claim_task(conn, executor, claimer="executor")
        task = kb.get_task(conn, executor)
        requested_events = _events(conn, executor, "plan_audit_requested")

    assert claimed is None
    assert task is not None
    assert task.status == "ready"
    assert task.block_kind is None
    assert requested_events[-1].payload == {"rejected_rounds": 1, "limit": 2}


def test_unique_rejected_rounds_exhaust_to_needs_input(kanban_home):
    with kb.connect() as conn:
        executor = kb.create_task(
            conn,
            title="executor with exhausted audit",
            assignee="executor",
            plan_audit_required=True,
            plan_audit_max_rounds=2,
        )

        kb.record_plan_audit_verdict(
            conn,
            executor,
            approved=False,
            metadata={"round": 1, "kind": "revise_plan"},
        )
        kb.record_plan_audit_verdict(
            conn,
            executor,
            approved=False,
            metadata={"round": 2, "kind": "revise_plan"},
        )

        claimed = kb.claim_task(conn, executor, claimer="executor")
        task = kb.get_task(conn, executor)
        exhausted = _events(conn, executor, "plan_audit_exhausted")

    assert claimed is None
    assert task is not None
    assert task.status == "blocked"
    assert task.block_kind == "needs_input"
    assert exhausted[-1].payload == {"rejected_rounds": 2, "limit": 2}


def test_plan_audit_actuator_reject_revision_is_idempotent_then_approval_opens_gate(
    kanban_home,
):
    with kb.connect() as conn:
        root = kb.create_task(conn, title="root coding goal", assignee="lead")
        auditor = kb.create_task(conn, title="audit round 1", assignee="auditor")
        executor = kb.create_task(
            conn,
            title="executor",
            assignee="executor",
            parents=(auditor,),
            plan_audit_required=True,
            plan_audit_max_rounds=2,
        )
        assert kb.claim_task(conn, executor, claimer="executor") is None

        result = kb.apply_plan_audit_actuation(
            conn,
            executor_task_id=executor,
            auditor_task_id=auditor,
            root_task_id=root,
            approved=False,
            reviewer="auditor",
            reason="plan needs concrete files",
            metadata={"round": 1, "kind": "revise_plan"},
            planner_assignee="planner",
            auditor_assignee="auditor",
        )
        replay = kb.apply_plan_audit_actuation(
            conn,
            executor_task_id=executor,
            auditor_task_id=auditor,
            root_task_id=root,
            approved=False,
            reviewer="auditor",
            reason="plan needs concrete files",
            metadata={"round": 1, "kind": "revise_plan"},
            planner_assignee="planner",
            auditor_assignee="auditor",
        )
        assert result.action == "revision_created"
        assert replay.action == "revision_created"
        assert result.planner_task_id == replay.planner_task_id
        assert result.auditor_revision_task_id == replay.auditor_revision_task_id
        assert result.auditor_completed is True

        planner_key = f"koc:{root}:{executor}:plan-round:2:planner"
        auditor_key = f"koc:{root}:{executor}:plan-round:2:auditor"
        planner_r2 = result.planner_task_id
        auditor_r2 = result.auditor_revision_task_id
        assert planner_r2 is not None
        assert auditor_r2 is not None
        assert kb.get_task(conn, executor).status == "todo"

        assert _count_tasks_with_key(conn, planner_key) == 1
        assert _count_tasks_with_key(conn, auditor_key) == 1
        assert len(_events(conn, executor, "plan_audit_rejected")) == 1
        auditor_after_replay = kb.get_task(conn, auditor)
        assert auditor_after_replay is not None
        assert auditor_after_replay.status == "done"

        assert kb.complete_task(conn, planner_r2, summary="round 2 plan ready")
        assert kb.complete_task(conn, auditor_r2, summary="round 2 audit approved")
        ready_executor = kb.get_task(conn, executor)
        assert ready_executor is not None
        assert ready_executor.status == "ready"

        kb.record_plan_audit_verdict(
            conn,
            executor,
            approved=True,
            reviewer="auditor",
            reason="round 2 plan is concrete",
            metadata={"round": 2},
        )
        claimed = kb.claim_task(conn, executor, claimer="executor")
        executor_after_approval = kb.get_task(conn, executor)

    assert claimed is not None
    assert executor_after_approval is not None
    assert executor_after_approval.status == "running"


def test_plan_audit_actuator_human_input_blocks_and_completes_auditor(kanban_home):
    with kb.connect() as conn:
        root = kb.create_task(conn, title="root coding goal", assignee="lead")
        executor = kb.create_task(
            conn,
            title="executor needing user decision",
            assignee="executor",
            plan_audit_required=True,
        )
        auditor = kb.create_task(conn, title="audit plan", assignee="auditor")
        assert kb.claim_task(conn, auditor, claimer="auditor") is not None

        result = kb.apply_plan_audit_actuation(
            conn,
            executor_task_id=executor,
            auditor_task_id=auditor,
            root_task_id=root,
            approved=False,
            reviewer="auditor",
            reason="needs product decision",
            metadata={"round": 1, "kind": "needs_user_decision"},
            comment="PLAN AUDIT NEEDS INPUT: choose between API A and API B.",
        )

        executor_after_block = kb.get_task(conn, executor)
        auditor_after_completion = kb.get_task(conn, auditor)
        comments = kb.list_comments(conn, executor)

    assert result.action == "blocked"
    assert executor_after_block is not None
    assert executor_after_block.status == "blocked"
    assert executor_after_block.block_kind == "needs_input"
    assert auditor_after_completion is not None
    assert auditor_after_completion.status == "done"
    assert comments[-1].body.startswith("PLAN AUDIT NEEDS INPUT:")


def test_plan_audit_actuator_replay_does_not_duplicate_comments(kanban_home):
    with kb.connect() as conn:
        root = kb.create_task(conn, title="root coding goal", assignee="lead")
        auditor = kb.create_task(conn, title="audit plan", assignee="auditor")
        executor = kb.create_task(
            conn,
            title="executor needing user decision",
            assignee="executor",
            plan_audit_required=True,
        )
        comment = "PLAN AUDIT NEEDS INPUT: choose between API A and API B."

        first = kb.apply_plan_audit_actuation(
            conn,
            executor_task_id=executor,
            auditor_task_id=auditor,
            root_task_id=root,
            approved=False,
            reviewer="auditor",
            reason="needs product decision",
            metadata={"round": 1, "kind": "needs_user_decision"},
            comment=comment,
        )
        replay = kb.apply_plan_audit_actuation(
            conn,
            executor_task_id=executor,
            auditor_task_id=auditor,
            root_task_id=root,
            approved=False,
            reviewer="auditor",
            reason="needs product decision",
            metadata={"round": 1, "kind": "needs_user_decision"},
            comment=comment,
        )
        comments = kb.list_comments(conn, executor)

    assert first.comment_id is not None
    assert replay.comment_id == first.comment_id
    assert [c.body for c in comments].count(comment) == 1


def test_plan_audit_block_preserves_block_recurrence_signal(kanban_home):
    with kb.connect() as conn:
        root = kb.create_task(conn, title="root coding goal", assignee="lead")
        auditor = kb.create_task(conn, title="audit plan", assignee="auditor")
        executor = kb.create_task(
            conn,
            title="executor with prior unblock loop",
            assignee="executor",
            plan_audit_required=True,
        )
        assert kb.block_task(
            conn,
            executor,
            reason="first needs input",
            kind="needs_input",
        )
        assert kb.unblock_task(conn, executor)

        result = kb.apply_plan_audit_actuation(
            conn,
            executor_task_id=executor,
            auditor_task_id=auditor,
            root_task_id=root,
            approved=False,
            reviewer="auditor",
            reason="needs product decision",
            metadata={"round": 1, "kind": "needs_user_decision"},
            comment="PLAN AUDIT NEEDS INPUT: choose between API A and API B.",
        )
        task = kb.get_task(conn, executor)
        loop_events = _events(conn, executor, "block_loop_detected")

    assert result.action == "blocked"
    assert task is not None
    assert task.status == "triage"
    assert task.block_kind == "needs_input"
    assert task.block_recurrences >= kb.BLOCK_RECURRENCE_LIMIT
    assert loop_events[-1].payload["source"] == "plan_audit"


def _failed_worker_for_escalation(conn):
    root = kb.create_task(
        conn,
        title="root escalation workflow",
        assignee="orchestrator",
        workflow_template_id="kanban-orchestrated-coding",
    )
    worker = kb.create_task(
        conn,
        title="worker exhausted repair attempts",
        body="Fix the failing acceptance test.",
        assignee="cheap-worker",
        workspace_kind="dir",
        workspace_path="C:/tmp/escalation-workspace",
        workflow_template_id="kanban-orchestrated-coding",
        current_step_key="worker",
    )
    with kb.write_txn(conn):
        run_id = kb._synthesize_ended_run(
            conn,
            worker,
            outcome="failed",
            error="pytest:test_add still failing",
            metadata={
                "failure_class": "task_failure",
                "error_signature": "pytest:test_add",
                "hypothesis": "off-by-one",
                "action_summary": "changed loop bound",
                "artifact_refs": ["artifacts/pytest-2.json"],
            },
        )
        conn.execute(
            "UPDATE tasks SET status='blocked', block_kind='capability' WHERE id=?",
            (worker,),
        )
    return root, worker, run_id


def test_worker_escalation_creates_idempotent_read_only_expert_handoff(
    kanban_home,
):
    with kb.connect() as conn:
        root, worker, run_id = _failed_worker_for_escalation(conn)
        first = kb.create_worker_escalation(
            conn,
            root_task_id=root,
            worker_task_id=worker,
            evidence_run_id=run_id,
            reason="retry_budget_exhausted",
            escalation_round=1,
            expert_assignee="expert-reviewer",
        )
        replay = kb.create_worker_escalation(
            conn,
            root_task_id=root,
            worker_task_id=worker,
            evidence_run_id=run_id,
            reason="retry_budget_exhausted",
            escalation_round=1,
            expert_assignee="expert-reviewer",
        )
        expert = kb.get_task(conn, first.expert_task_id)
        outbound = _events(conn, worker, "role_handoff")
        inbound = _events(conn, first.expert_task_id, "role_handoff")
        key = f"koc:{root}:{worker}:worker-escalation:1:expert"
        task_count = _count_tasks_with_key(conn, key)

    assert replay.expert_task_id == first.expert_task_id
    assert task_count == 1
    assert expert is not None
    assert expert.current_step_key == "reviewer"
    assert "Produce a repair plan only; do not edit production code" in expert.body
    assert "pytest:test_add" in expert.body
    assert len(outbound) == 1
    assert len(inbound) == 1
    assert outbound[0].payload["from_role"] == "worker"
    assert outbound[0].payload["to_role"] == "reviewer"
    assert outbound[0].payload["reason"] == "retry_budget_exhausted"
    assert outbound[0].payload["evidence_reference"] == f"task_run:{run_id}"
    assert isinstance(outbound[0].payload["timestamp"], int)


def test_expert_repair_plan_creates_one_cheap_worker_with_parent_handoff(
    kanban_home,
):
    with kb.connect() as conn:
        root, worker, run_id = _failed_worker_for_escalation(conn)
        escalation = kb.create_worker_escalation(
            conn,
            root_task_id=root,
            worker_task_id=worker,
            evidence_run_id=run_id,
            reason="same_error_signature",
        )
        first = kb.apply_expert_repair_plan(
            conn,
            root_task_id=root,
            worker_task_id=worker,
            expert_task_id=escalation.expert_task_id,
            repair_plan="Restore add() semantics, then rerun pytest.",
            repair_assignee="cheap-worker",
        )
        replay = kb.apply_expert_repair_plan(
            conn,
            root_task_id=root,
            worker_task_id=worker,
            expert_task_id=escalation.expert_task_id,
            repair_plan="Restore add() semantics, then rerun pytest.",
            repair_assignee="cheap-worker",
        )
        expert = kb.get_task(conn, escalation.expert_task_id)
        repair = kb.get_task(conn, first.repair_task_id)
        expert_run = kb.latest_run(conn, escalation.expert_task_id)
        handoffs = _events(conn, escalation.expert_task_id, "role_handoff")
        key = f"koc:{root}:{worker}:worker-escalation:1:repair"
        task_count = _count_tasks_with_key(conn, key)

        repair_parents = kb.parent_ids(conn, first.repair_task_id)

    assert replay.repair_task_id == first.repair_task_id
    assert task_count == 1
    assert expert is not None and expert.status == "done"
    assert expert_run is not None
    assert expert_run.metadata["mode"] == "read_only"
    assert repair is not None
    assert repair.status == "ready"
    assert repair.assignee == "cheap-worker"
    assert repair.current_step_key == "worker"
    assert repair.workspace_kind == "dir"
    assert repair.workspace_path == "C:/tmp/escalation-workspace"
    assert repair_parents == [escalation.expert_task_id]
    outbound = [event for event in handoffs if event.payload["direction"] == "outbound"]
    assert len(outbound) == 1
    assert outbound[0].payload["from_role"] == "reviewer"
    assert outbound[0].payload["to_role"] == "worker"
    assert outbound[0].payload["evidence_reference"] == f"task_run:{expert_run.id}"


def test_worker_escalation_rejects_foreign_or_open_evidence_run(kanban_home):
    with kb.connect() as conn:
        root, worker, _run_id = _failed_worker_for_escalation(conn)
        other = kb.create_task(conn, title="other worker", assignee="worker")
        foreign_run = kb._synthesize_ended_run(conn, other, outcome="failed")
        with pytest.raises(ValueError, match="belonging to task"):
            kb.create_worker_escalation(
                conn,
                root_task_id=root,
                worker_task_id=worker,
                evidence_run_id=foreign_run,
                reason="retry_budget_exhausted",
            )
