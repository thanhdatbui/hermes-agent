"""Deterministic Claude Code lane contracts; no live CLI or provider calls."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


EDGE_PATH = Path(__file__).resolve().parents[2] / "plugins" / "autonomous-ai-agents" / "kanban-claude-lane" / "edge.py"
SPEC = importlib.util.spec_from_file_location("kanban_claude_lane_edge", EDGE_PATH)
assert SPEC and SPEC.loader
edge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(edge)

UNSTAGED_DIFF_COMMAND = (
    'python -c "import subprocess,sys; '
    "sys.exit(0 if subprocess.run(['git','diff','--quiet','--','allowed.txt']).returncode == 1 else 1)\""
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "test@example.invalid")
    _git(path, "config", "user.name", "Test")
    (path / "allowed.txt").write_text("base\n", encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "-qm", "base")
    return path


def _setup(monkeypatch: pytest.MonkeyPatch, behavior: str, artifact_home: Path) -> dict[str, bool]:
    killed = {"value": False}
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_claude")
    monkeypatch.setattr(edge, "get_hermes_home", lambda: artifact_home)
    monkeypatch.setattr(edge, "_config", lambda: {"enabled": True, "executable": "claude", "timeout_seconds": 5, "max_turns": 3, "allowed_tools": ["Read", "Edit"]})
    monkeypatch.setattr(edge.shutil, "which", lambda _: "claude")
    original = edge._run
    monkeypatch.setattr(edge, "_run", lambda command, *, cwd: subprocess.CompletedProcess(command, 0, "claude test", "") if command[-1] == "--version" else original(command, cwd=cwd))

    def spawn(_command, *, cwd, **_kwargs):
        lane = Path(cwd)
        if behavior == "success":
            (lane / "allowed.txt").write_text("changed\n", encoding="utf-8")
            _git(lane, "add", "allowed.txt")
            _git(lane, "commit", "-qm", "claude change")
        elif behavior == "uncommitted":
            (lane / "allowed.txt").write_text("uncommitted\n", encoding="utf-8")
        elif behavior == "forbidden":
            (lane / "forbidden.txt").write_text("blocked\n", encoding="utf-8")
            _git(lane, "add", "forbidden.txt")
            _git(lane, "commit", "-qm", "forbidden claude change")
        elif behavior == "renamed_forbidden":
            _git(lane, "mv", "allowed.txt", "renamed.txt")
            _git(lane, "commit", "-qm", "rename forbidden claude path")
        return SimpleNamespace(id="proc-claude")

    monkeypatch.setattr(edge.process_registry, "spawn_local", spawn)
    if behavior == "timeout":
        response = {"status": "timeout", "output": ""}
    elif behavior == "json_fail":
        response = {"status": "exited", "exit_code": 0, "output": "not json"}
    else:
        response = {"status": "exited", "exit_code": 0, "output": json.dumps({"type": "result", "usage": {"input_tokens": 2}, "total_cost_usd": 0.01, "session_id": "s1", "modelUsage": {"test": {}}})}
    monkeypatch.setattr(edge.process_registry, "wait", lambda *_args, **_kwargs: response)
    monkeypatch.setattr(edge.process_registry, "kill_process", lambda *_args, **_kwargs: killed.update(value=True) or {"status": "killed"})
    return killed


def _call(repo: Path, **extra) -> dict:
    raw = edge.run_claude_lane({"prompt": "bounded", "workspace": str(repo), **extra})
    return json.loads(raw)["metadata"]["claude_lane"]


def test_success_parses_cost_and_runs_hermes_test(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "success", repo.parent / "hermes-home")
    metadata = _call(repo, test_commands=["git diff --check"])
    assert metadata["result"] == "accepted" and metadata["accepted_commits"]
    assert metadata["cost_usd"] == 0.01 and metadata["usage"]["input_tokens"] == 2
    assert metadata["tests_run"][0]["owner"] == "hermes"
    assert (repo / "allowed.txt").read_text(encoding="utf-8") == "changed\n"
    assert subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    assert not Path(metadata["worktree"]).exists()
    assert len(metadata["artifacts"]) == 2
    assert all(Path(path).is_file() for path in metadata["artifacts"])
    monkeypatch.setattr(
        edge.process_registry,
        "spawn_local",
        lambda *_args, **_kwargs: pytest.fail("accepted diff must block a blind retry"),
    )
    retry = json.loads(edge.run_claude_lane({"prompt": "retry", "workspace": str(repo)}))
    assert "resolve the existing diff instead of retrying" in retry["error"]


def test_uncommitted_diff_is_reconciled_without_commit_evidence(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "uncommitted", repo.parent / "hermes-home")
    metadata = _call(repo, test_commands=[UNSTAGED_DIFF_COMMAND])
    assert metadata["result"] == "accepted"
    assert metadata["accepted_commits"] == []
    assert metadata["tests_run"] == [{"command": UNSTAGED_DIFF_COMMAND, "exit_code": 0, "owner": "hermes"}]
    assert (repo / "allowed.txt").read_text(encoding="utf-8") == "uncommitted\n"
    assert not Path(metadata["worktree"]).exists()
    assert len(metadata["artifacts"]) == 2
    assert all(Path(path).is_file() for path in metadata["artifacts"])


@pytest.mark.parametrize("commit_source", [False, True], ids=["dirty", "head-changed"])
def test_source_change_during_lane_preserves_patch_without_reconciling(
    repo: Path, monkeypatch: pytest.MonkeyPatch, commit_source: bool,
) -> None:
    _setup(monkeypatch, "uncommitted", repo.parent / "hermes-home")
    original_wait = edge.process_registry.wait

    def wait(*args, **kwargs):
        (repo / "concurrent.txt").write_text("user change\n", encoding="utf-8")
        if commit_source:
            _git(repo, "add", "concurrent.txt")
            _git(repo, "commit", "-qm", "concurrent source change")
        return original_wait(*args, **kwargs)

    monkeypatch.setattr(edge.process_registry, "wait", wait)
    metadata = _call(repo)
    assert metadata["result"] == "rejected"
    assert "source workspace changed while the claude lane was running" in metadata["rejected_reason"].lower()
    assert (repo / "allowed.txt").read_text(encoding="utf-8") == "base\n"
    assert len(metadata["artifacts"]) == 2
    assert any(Path(path).suffix == ".patch" and Path(path).is_file() for path in metadata["artifacts"])
    assert not Path(metadata["worktree"]).exists()


def test_timeout_kills_and_cleans(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    killed = _setup(monkeypatch, "timeout", repo.parent / "hermes-home")
    metadata = _call(repo)
    assert metadata["result"] == "timed_out" and killed["value"]
    assert not Path(metadata["worktree"]).exists()


def test_forbidden_diff_is_rejected(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "forbidden", repo.parent / "hermes-home")
    metadata = _call(repo, forbidden_paths=["forbidden.txt"])
    assert metadata["result"] == "rejected" and "forbidden.txt" in metadata["rejected_reason"]
    assert not (repo / "forbidden.txt").exists()
    assert not Path(metadata["worktree"]).exists()


def test_renamed_forbidden_path_is_rejected(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "renamed_forbidden", repo.parent / "hermes-home")
    metadata = _call(repo, forbidden_paths=["allowed.txt"])
    assert metadata["result"] == "rejected"
    assert "allowed.txt" in metadata["rejected_reason"]
    assert (repo / "allowed.txt").read_text(encoding="utf-8") == "base\n"
    assert not Path(metadata["worktree"]).exists()


def test_dirty_source_is_rejected_before_spawn(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "success", repo.parent / "hermes-home")
    monkeypatch.setattr(
        edge.process_registry,
        "spawn_local",
        lambda *_args, **_kwargs: pytest.fail("dirty workspace must not spawn Claude"),
    )
    (repo / "dirty.txt").write_text("local work\n", encoding="utf-8")
    result = json.loads(edge.run_claude_lane({"prompt": "bounded", "workspace": str(repo)}))
    assert "workspace must be clean" in result["error"]


def test_invalid_json_is_rejected(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "json_fail", repo.parent / "hermes-home")
    metadata = _call(repo)
    assert metadata["result"] == "rejected" and "valid JSON" in metadata["rejected_reason"]


def test_branch_name_is_portable() -> None:
    name = edge.build_branch_name("t: unsafe/path")
    assert name.startswith("claude/t-unsafe-path/") and ":" not in name and " " not in name
