import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

_spec = importlib.util.spec_from_file_location("cm", Path(__file__).parent / "__init__.py")
cm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cm)


# Step 1: Done trigger matching
def test_done_signal_variants():
    for t in ("Done", "done.", " XONG ", "xong!", "Chốt phiên"):
        assert cm.is_done_signal(t), t
    for t in ("done with the first part, continue", "chưa xong", ""):
        assert not cm.is_done_signal(t), t


def test_classify_staged_blocked_failed_ok():
    staged = json.dumps({"success": True, "staged": True, "pending_id": "2f610d81"})
    assert cm.classify_result(staged) == "STAGED"
    assert cm.classify_result({"action": "block"}) == "BLOCKED"
    assert cm.classify_result(json.dumps({"success": False, "error": "x"})) == "FAILED"
    assert cm.classify_result(json.dumps({"exit_code": 1})) == "FAILED"
    assert cm.classify_result(json.dumps({"success": True})) == "OK"


# Step 2: claim validator vs tool receipts
def test_claim_after_staged_is_replaced():
    r = [{"tool": "patch", "status": "BLOCKED"}, {"tool": "memory", "status": "STAGED"}]
    out = cm.validate_claim("Đã cơ giới hóa xong, đã đưa vào Memory", r)
    assert out and "UNPROVEN_STAGED" in out


def test_claim_without_any_tool_is_replaced():
    out = cm.validate_claim("Đã xong.", [])
    assert out and "NO_RECEIPT" in out


def test_claim_with_ok_mutating_tool_passes():
    assert cm.validate_claim("Đã sửa xong", [{"tool": "patch", "status": "OK"}]) is None


def test_non_claim_text_passes():
    assert cm.validate_claim("Đang kiểm tra log.", []) is None


# Step 2b: push only after APPROVED, never commit
def test_run_closeout_pushes_only_when_approved(monkeypatch):
    pushed = []
    monkeypatch.setattr(cm, "push_if_ahead", lambda r: pushed.append(r) or "PUSHED:origin/main")
    monkeypatch.setattr(cm, "dirty_count", lambda r: 2)

    def fake_run(cmd, **kw):
        rc = 0 if "good" in cmd else 1
        return SimpleNamespace(returncode=rc, stdout='{"verdict": "X"}')

    monkeypatch.setattr(cm.subprocess, "run", fake_run)
    out = cm.run_closeout(["good", "bad"])
    assert pushed == ["good"]
    assert "SKIPPED_GATE_NOT_APPROVED" in out and "PUSHED:origin/main" in out and "REJECTED" in out


# Step 3: gateway dispatch hook (rewrite so LLM still writes the session report)
def test_gateway_hook_rewrites_and_replies(monkeypatch):
    monkeypatch.setattr(cm, "run_closeout", lambda repos=None: "VERDICT")
    adapter = SimpleNamespace(send=AsyncMock())
    gw = SimpleNamespace(_adapter_for_source=lambda s: adapter)
    ev = SimpleNamespace(text="Done", source=SimpleNamespace(chat_id="c1"))

    async def run():
        res = cm._on_pre_gateway_dispatch(event=ev, gateway=gw)
        await asyncio.sleep(0.2)
        return res

    res = asyncio.run(run())
    assert res["action"] == "rewrite" and res["text"] == cm.CLOSEOUT_REWRITE_TEXT
    adapter.send.assert_awaited_once_with("c1", "VERDICT", reply_to=None, metadata={})


# Step 4: gateway dispatch hook with topic and reply_to
def test_gateway_hook_with_topic_and_reply_to(monkeypatch):
    monkeypatch.setattr(cm, "run_closeout", lambda repos=None: "VERDICT")
    adapter = SimpleNamespace(send=AsyncMock())
    gw = SimpleNamespace(_adapter_for_source=lambda s: adapter)
    ev = SimpleNamespace(
        text="Done",
        message_id="m123",
        source=SimpleNamespace(chat_id="c1", thread_id="t456"),
    )

    async def run():
        res = cm._on_pre_gateway_dispatch(event=ev, gateway=gw)
        await asyncio.sleep(0.2)
        return res

    res = asyncio.run(run())
    assert res["action"] == "rewrite" and res["text"] == cm.CLOSEOUT_REWRITE_TEXT
    adapter.send.assert_awaited_once_with(
        "c1",
        "VERDICT",
        reply_to="m123",
        metadata={"thread_id": "t456"},
    )


def test_transform_is_log_only_by_default(monkeypatch):
    monkeypatch.delenv("CLOSEOUT_MECH_ENFORCE", raising=False)
    assert cm._on_transform_llm_output("Đã xong.", session_id="s_log") is None


def test_transform_enforces_when_flag_set(monkeypatch):
    monkeypatch.setenv("CLOSEOUT_MECH_ENFORCE", "1")
    out = cm._on_transform_llm_output("Đã xong.", session_id="s_enf")
    assert out and "NO_RECEIPT" in out


def test_gateway_hook_ignores_normal_text():
    ev = SimpleNamespace(text="sửa file giúp tao", source=None)
    assert cm._on_pre_gateway_dispatch(event=ev, gateway=None) is None


# Step 5: Scope Lock - only repos the session mutated are gated
def test_repos_in_args_matches_only_named_repos(tmp_path):
    for n in ("tools", "tiktok-follow", "GPM auto"):
        (tmp_path / n / ".git").mkdir(parents=True)
    root = str(tmp_path)
    args = {"path": root.replace("\\", "/") + "/tools/x.py", "cmd": f'cd "{root}\GPM auto" && ls'}
    found = cm.repos_in_args(args, root=root)
    assert sorted(Path(f).name for f in found) == ["GPM auto", "tools"]


def test_scope_records_only_mutating_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "_save_scope", lambda: None)
    monkeypatch.setattr(cm, "repos_in_args", lambda a, root=None: ["R1"])
    cm._on_post_tool_call(tool_name="read_file", result="{}", session_id="sA", args={"p": "x"})
    assert cm.session_repos("sA") == []
    cm._on_post_tool_call(tool_name="patch", result="{}", session_id="sA", args={"p": "x"})
    assert cm.session_repos("sA") == ["R1"]


def test_run_closeout_no_repos_does_not_sweep():
    out = cm.run_closeout([])
    assert "KHONG_CO_VIEC" in out and "Scope Lock" in out


def test_infer_repos_from_transcript_uses_only_mutating_calls(tmp_path):
    for n in ("mine", "other"):
        (tmp_path / n / ".git").mkdir(parents=True)
    root = str(tmp_path)
    base = root.replace("\\", "/")
    msgs = [
        {"role": "assistant", "tool_calls": [{"function": {"name": "patch", "arguments": '{"path": "%s/mine/a.py"}' % base}}]},
        {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "%s/other/b.py"}' % base}}]},
    ]
    got = cm.infer_repos_from_transcript(msgs, root=root)
    assert [Path(g).name for g in got] == ["mine"]
