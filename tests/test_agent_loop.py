import copy
import json

from scripts.agent_loop import (
    AdapterFailure,
    AdapterFailureKind,
    AgentLoop,
    FileStateStore,
    Finding,
    RoleConfig,
    RoleSpec,
    Verdict,
    VerdictStatus,
)


class MemoryStore:
    def __init__(self):
        self.state = None
        self.artifacts = {}

    def load(self):
        return copy.deepcopy(self.state)

    def save(self, state):
        self.state = copy.deepcopy(state)

    def write_artifact(self, round_number, phase, payload):
        path = f"artifacts/round-{round_number:03d}-{phase}.json"
        self.artifacts[path] = copy.deepcopy(payload)
        return path


class ScriptedAdapter:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def run(self, role, task, context):
        self.calls.append((role, task, context))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def finding(finding_id, summary):
    return Finding(finding_id, summary)


def response(finding_id, disposition, rationale, *, output=None):
    payload = {
        "responses": [
            {
                "finding_id": finding_id,
                "disposition": disposition,
                "rationale": rationale,
            }
        ]
    }
    if output is not None:
        payload["output"] = output
    return payload


def test_worker_answers_each_finding_and_reviewer_rechecks_consensus():
    audit = Verdict(
        VerdictStatus.CHANGES_REQUESTED,
        "Hai phát hiện cần xử lý",
        findings=(finding("F1", "Thiếu test"), finding("F2", "Nhận định sai")),
    )
    worker_response = {
        "summary": "Đã xử lý từng phát hiện",
        "responses": [
            {
                "finding_id": "F1",
                "disposition": "ACCEPT",
                "rationale": "Đã thêm test",
                "evidence": ["tests/test_agent_loop.py"],
            },
            {
                "finding_id": "F2",
                "disposition": "REJECT",
                "rationale": "Bằng chứng hiện tại bác bỏ phát hiện",
            },
        ],
        "output": {"revision": 2},
    }
    adapter = ScriptedAdapter([
        {"revision": 1},
        audit,
        worker_response,
        Verdict(VerdictStatus.APPROVED, "Đã đạt đồng thuận"),
    ])
    store = MemoryStore()

    result = AgentLoop(adapter, store).run("build prototype")

    assert result.status == "APPROVED"
    assert result.output == {"revision": 2}
    assert [call[2]["phase"] for call in adapter.calls] == [
        "implementation",
        "audit",
        "finding_response",
        "consensus",
    ]
    consensus_context = adapter.calls[-1][2]
    dispositions = {
        item["finding_id"]: item["disposition"]
        for item in consensus_context["finding_responses"]["responses"]
    }
    assert dispositions == {"F1": "ACCEPT", "F2": "REJECT"}
    assert len(store.artifacts) == 4


def test_consensus_feedback_drives_next_implementation_and_rounds_are_bounded():
    first_audit = Verdict(
        VerdictStatus.CHANGES_REQUESTED,
        "Cần sửa",
        findings=(finding("F1", "Thiếu kiểm tra"),),
    )
    first_consensus = Verdict(
        VerdictStatus.CHANGES_REQUESTED,
        "Chưa đạt đồng thuận",
        "Bổ sung kiểm tra thật",
        findings=(finding("F1", "Thiếu kiểm tra"),),
    )
    adapter = ScriptedAdapter([
        "draft 1",
        first_audit,
        response("F1", "ACCEPT", "Sẽ bổ sung"),
        first_consensus,
        "draft 2",
        first_audit,
        response("F1", "ACCEPT", "Đã bổ sung"),
        first_consensus,
    ])

    result = AgentLoop(adapter, MemoryStore(), max_rounds=2).run("task")

    assert result.status == "MAX_ROUNDS"
    assert result.rounds == 2
    second_implementation = adapter.calls[4][2]
    assert second_implementation["feedback"] == "Bổ sung kiểm tra thật"
    assert second_implementation["previous_output"] == "draft 1"


def test_role_configuration_is_backend_agnostic_and_not_persisted_with_secrets():
    roles = RoleConfig(
        worker=RoleSpec("implementer", "local", {"temperature": 0}),
        reviewer=RoleSpec("auditor", "provider-a", {"api_key": "secret"}),
        fallback_reviewer=RoleSpec("backup", "provider-b"),
    )
    adapter = ScriptedAdapter(["draft", Verdict(VerdictStatus.APPROVED, "ok")])
    store = MemoryStore()

    result = AgentLoop(adapter, store, roles=roles).run("task")

    assert result.status == "APPROVED"
    assert [(call[0].name, call[0].backend) for call in adapter.calls] == [
        ("implementer", "local"),
        ("auditor", "provider-a"),
    ]
    serialized = json.dumps(store.state)
    assert "api_key" in serialized
    assert "secret" not in serialized


def test_quota_failure_selects_fallback_for_audit_and_consensus():
    audit = Verdict(
        VerdictStatus.CHANGES_REQUESTED,
        "Cần sửa",
        findings=(finding("F1", "Thiếu test"),),
    )
    adapter = ScriptedAdapter([
        "draft",
        AdapterFailure("quota exhausted", AdapterFailureKind.QUOTA),
        audit,
        response("F1", "ACCEPT", "Đã sửa", output="revised"),
        Verdict(VerdictStatus.APPROVED, "fallback đồng ý"),
    ])
    roles = RoleConfig(reviewer="strict", fallback_reviewer="backup")

    result = AgentLoop(adapter, MemoryStore(), roles=roles).run("task")

    assert result.status == "APPROVED"
    assert result.reviewer_role == "backup"
    assert [call[0].name for call in adapter.calls] == [
        "worker",
        "strict",
        "backup",
        "worker",
        "backup",
    ]
    audit_state = result.state["rounds"][0]["audit"]
    assert audit_state["fallback_used"] is True
    assert audit_state["failures"][0]["kind"] == "quota"


def test_all_reviewer_routes_failing_persists_final_blocked():
    adapter = ScriptedAdapter([
        "draft",
        AdapterFailure("provider down"),
        AdapterFailure("backup down"),
    ])
    store = MemoryStore()

    result = AgentLoop(adapter, store).run("task")

    assert result.status == "FINAL_BLOCKED"
    assert store.state["stop_reason"] == "audit"
    assert store.state["rounds"][0]["error"]["error"]["failures"]


def test_worker_must_respond_exactly_once_to_every_finding():
    audit = Verdict(
        VerdictStatus.CHANGES_REQUESTED,
        "Cần sửa",
        findings=(finding("F1", "Một"), finding("F2", "Hai")),
    )
    adapter = ScriptedAdapter([
        "draft",
        audit,
        response("F1", "ACCEPT", "Chỉ trả lời một finding"),
    ])

    result = AgentLoop(adapter, MemoryStore()).run("task")

    assert result.status == "FINAL_BLOCKED"
    assert result.state["stop_reason"] == "finding_response"


def test_file_store_writes_state_and_phase_artifacts_under_run_directory(tmp_path):
    store = FileStateStore.for_task(
        "durable task", root=tmp_path / ".hermes/agent-loop"
    )
    adapter = ScriptedAdapter(["draft", Verdict(VerdictStatus.APPROVED, "ok")])

    result = AgentLoop(adapter, store).run("durable task")

    assert result.status == "APPROVED"
    assert store.path.exists()
    assert store.run_dir.parent == tmp_path / ".hermes/agent-loop"
    artifacts = sorted((store.run_dir / "artifacts").glob("*.json"))
    assert [path.name for path in artifacts] == [
        "round-001-audit.json",
        "round-001-implementation.json",
    ]
    resumed = AgentLoop(ScriptedAdapter([]), store).run("durable task")
    assert resumed.status == "APPROVED"
    assert resumed.rounds == 1
