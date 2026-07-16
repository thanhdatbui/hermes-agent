"""Deterministic contract tests for the optional Codex edge lane."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


EDGE_PATH = (
    Path(__file__).resolve().parents[2] / "plugins" / "autonomous-ai-agents"
    / "kanban-codex-lane" / "edge.py"
)
_SPEC = importlib.util.spec_from_file_location("kanban_codex_lane_edge", EDGE_PATH)
assert _SPEC and _SPEC.loader
edge = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(edge)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "allowed.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "base")
    return repo


def _install_fakes(monkeypatch: pytest.MonkeyPatch, *, behavior: str, timeout: int = 5) -> dict:
    killed: dict[str, bool] = {"value": False}
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_lane")
    monkeypatch.setattr(edge, "_codex_config", lambda: {
        "enabled": True, "executable": "codex", "mode": "exec", "timeout_seconds": timeout,
    })
    monkeypatch.setattr(edge.shutil, "which", lambda _: "codex")
    original_run = edge._run

    def fake_run(command, *, cwd):
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, "codex test", "")
        return original_run(command, cwd=cwd)

    monkeypatch.setattr(edge, "_run", fake_run)

    def spawn(_command, *, cwd, **_kwargs):
        lane = Path(cwd)
        if behavior == "success":
            (lane / "allowed.txt").write_text("changed\n", encoding="utf-8")
            _git(lane, "add", "allowed.txt")
            _git(lane, "commit", "-qm", "codex change")
        elif behavior == "rejected_diff":
            (lane / "forbidden.txt").write_text("nope\n", encoding="utf-8")
        return SimpleNamespace(id="proc-test")

    monkeypatch.setattr(edge.process_registry, "spawn_local", spawn)
    if behavior == "timeout":
        monkeypatch.setattr(edge.process_registry, "wait", lambda *_args, **_kwargs: {"status": "timeout", "output": ""})
    elif behavior == "provider_error":
        monkeypatch.setattr(edge.process_registry, "wait", lambda *_args, **_kwargs: {"status": "exited", "exit_code": 1, "output": "API key rejected"})
    else:
        monkeypatch.setattr(edge.process_registry, "wait", lambda *_args, **_kwargs: {"status": "exited", "exit_code": 0, "output": "done"})

    def kill(*_args, **_kwargs):
        killed["value"] = True
        return {"status": "killed"}

    monkeypatch.setattr(edge.process_registry, "kill_process", kill)
    return killed


def _call(repo: Path, **kwargs) -> dict:
    result = edge.run_codex_lane({"prompt": "bounded task", "workspace": str(repo), **kwargs})
    return json.loads(result)["metadata"]["codex_lane"]


def test_success_accepts_committed_diff_and_hermes_tests(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fakes(monkeypatch, behavior="success")
    metadata = _call(repo, test_commands=["git diff --check"])
    assert metadata["result"] == "accepted"
    assert metadata["accepted_commits"]
    assert metadata["tests_run"] == []
    assert not Path(metadata["worktree"]).exists()


def test_timeout_kills_process_and_cleans_worktree(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    killed = _install_fakes(monkeypatch, behavior="timeout")
    metadata = _call(repo)
    assert metadata["result"] == "timed_out"
    assert "timeout" in metadata["rejected_reason"].lower()
    assert killed["value"] is True
    assert not Path(metadata["worktree"]).exists()


def test_provider_error_is_rejected_without_commits(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fakes(monkeypatch, behavior="provider_error")
    metadata = _call(repo)
    assert metadata["result"] == "rejected"
    assert metadata["rejected_reason"]
    assert metadata["accepted_commits"] == []
    assert not Path(metadata["worktree"]).exists()


def test_forbidden_diff_is_not_gated_by_the_lane(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fakes(monkeypatch, behavior="rejected_diff")
    metadata = _call(repo, forbidden_paths=["forbidden.txt"])
    assert metadata["result"] == "accepted"
    assert not Path(metadata["worktree"]).exists()


def test_portable_names_are_filesystem_safe() -> None:
    branch = edge.build_branch_name("t: unsafe/path")
    assert branch.startswith("codex/t-unsafe-path/")
    assert ":" not in branch and " " not in branch
