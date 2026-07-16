"""Portable, opt-in Codex CLI input lane for a Kanban worker.

The lane is deliberately an edge integration: it uses existing process,
worktree, and Kanban metadata rails rather than adding lifecycle state to core.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home
from hermes_cli.config import load_config
from tools.environments.local import _sanitize_subprocess_env
from tools.process_registry import process_registry
from tools.registry import tool_error


_RESULTS = {"accepted", "partial", "rejected", "timed_out"}
_MODES = {"exec", "goal"}


def _codex_config() -> dict[str, Any]:
    config = load_config() or {}
    lane = ((config.get("kanban") or {}).get("external_lanes") or {}).get("codex")
    return lane if isinstance(lane, dict) else {}


def check_codex_lane() -> bool:
    """Expose the plugin tool only to an opted-in dispatcher worker."""
    config = _codex_config()
    return bool(os.getenv("HERMES_KANBAN_TASK")) and bool(config.get("enabled", False))


def _safe_task_id(task_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", task_id).strip("-")
    return cleaned or "task"


def build_branch_name(task_id: str, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"codex/{_safe_task_id(task_id)}/{timestamp}"


def build_worktree_path(task_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"hermes-codex-{_safe_task_id(task_id)}-{uuid.uuid4().hex[:8]}"


def validate_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Validate the edge-owned metadata contract before returning it to Hermes."""
    required = {
        "used", "mode", "worktree", "branch", "command", "result",
        "accepted_commits", "rejected_reason", "tests_run", "artifacts",
    }
    missing = required - set(metadata)
    if missing:
        raise ValueError(f"codex_lane metadata missing: {', '.join(sorted(missing))}")
    if not isinstance(metadata["used"], bool) or metadata["mode"] not in (*_MODES, "skipped"):
        raise ValueError("codex_lane metadata has invalid used or mode")
    if metadata["result"] not in _RESULTS:
        raise ValueError("codex_lane metadata has invalid result")
    if not all(isinstance(value, str) for value in metadata["accepted_commits"]):
        raise ValueError("codex_lane accepted_commits must be strings")
    if not isinstance(metadata["tests_run"], list) or not isinstance(metadata["artifacts"], list):
        raise ValueError("codex_lane tests_run and artifacts must be lists")
    return metadata


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, check=False,
        env=_sanitize_subprocess_env(os.environ), encoding="utf-8", errors="replace",
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=repo)


def _apply_patch(repo: Path, patch: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=repo,
        input=patch,
        text=True,
        capture_output=True,
        check=False,
        env=_sanitize_subprocess_env(os.environ),
        encoding="utf-8",
        errors="replace",
    )


def _artifact_path(task_id: str, suffix: str) -> Path:
    root = get_hermes_home() / "artifacts" / "external-lanes" / _safe_task_id(task_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"codex-{uuid.uuid4().hex[:12]}{suffix}"


def _metadata(*, mode: str, worktree: Path | None, branch: str | None,
              command: str | None, result: str, reason: str = "",
              commits: list[str] | None = None, tests: list[dict[str, Any]] | None = None,
              artifacts: list[str] | None = None) -> dict[str, Any]:
    return validate_metadata({
        "used": result != "rejected" or bool(worktree), "mode": mode,
        "worktree": str(worktree) if worktree else None, "branch": branch,
        "command": command, "result": result, "accepted_commits": commits or [],
        "rejected_reason": reason, "tests_run": tests or [], "artifacts": artifacts or [],
    })


def _run_tests(worktree: Path, commands: list[str]) -> tuple[list[dict[str, Any]], str]:
    evidence: list[dict[str, Any]] = []
    for command in commands:
        completed = subprocess.run(
            command, cwd=worktree, shell=True, text=True, capture_output=True, check=False,
            env=_sanitize_subprocess_env(os.environ), encoding="utf-8", errors="replace",
        )
        evidence.append({"command": command, "exit_code": completed.returncode, "owner": "hermes"})
        if completed.returncode:
            return evidence, f"Hermes verification failed: {command}"
    return evidence, ""


def run_codex_lane(args: dict[str, Any], task_id: str | None = None, **_: Any) -> str:
    """Run, review, and clean a one-shot Codex lane; never complete the task."""
    if not check_codex_lane():
        return tool_error("Codex lane is disabled or this is not a Kanban worker")
    task_id = task_id or os.getenv("HERMES_KANBAN_TASK", "")
    config = _codex_config()
    executable = str(config.get("executable") or "codex")
    resolved = shutil.which(executable)
    if not resolved:
        return tool_error("Codex executable is unavailable", executable=executable)
    mode = str(args.get("mode") or config.get("mode") or "exec")
    if mode not in _MODES:
        return tool_error("Codex lane mode must be exec or goal")
    source = Path(str(args.get("workspace") or "")).expanduser().resolve()
    if not source.is_dir() or _git(source, "rev-parse", "--is-inside-work-tree").returncode:
        return tool_error("workspace must be an existing git worktree")
    if _git(source, "status", "--porcelain").stdout.strip():
        return tool_error(
            "workspace must be clean before starting a Codex lane; "
            "resolve the existing diff instead of retrying"
        )
    base_sha = _git(source, "rev-parse", "HEAD").stdout.strip()
    version = _run([resolved, "--version"], cwd=source)
    if version.returncode:
        return tool_error("Codex capability check failed", executable=executable)

    worktree = build_worktree_path(task_id)
    branch = build_branch_name(task_id)
    prompt = str(args["prompt"])
    goal_flag = " --enable goals" if mode == "goal" else ""
    command = (
        f"{shlex.quote(resolved)}{goal_flag} exec --sandbox workspace-write "
        f"{shlex.quote(prompt)}"
    )
    timeout = max(1, int(config.get("timeout_seconds") or 300))
    tests = [str(item) for item in args.get("test_commands") or []]
    forbidden = {str(item) for item in args.get("forbidden_paths") or []}
    artifacts: list[str] = []
    metadata: dict[str, Any]
    created = False
    accepted = False
    try:
        added = _git(source, "worktree", "add", "-b", branch, str(worktree), "HEAD")
        if added.returncode:
            return tool_error("Could not create isolated Codex worktree", detail=added.stderr[-500:])
        created = True
        session = process_registry.spawn_local(command, cwd=str(worktree), task_id=task_id, use_pty=True)
        waited = process_registry.wait(session.id, timeout=timeout)
        output_path = _artifact_path(task_id, ".log")
        output_path.write_text(str(waited.get("output") or ""), encoding="utf-8")
        artifacts.append(str(output_path))
        if waited["status"] == "timeout":
            process_registry.kill_process(session.id, source="kanban_codex_lane.timeout")
            metadata = _metadata(mode=mode, worktree=worktree, branch=branch, command=command,
                                 result="timed_out", reason="Codex lane timeout", artifacts=artifacts)
        elif waited["status"] != "exited" or waited.get("exit_code") != 0:
            metadata = _metadata(mode=mode, worktree=worktree, branch=branch, command=command,
                                 result="rejected", reason="Codex CLI exited unsuccessfully", artifacts=artifacts)
        else:
            # Stage only inside the disposable lane so one diff covers
            # committed, modified, deleted, renamed, and untracked files.
            staged = _git(worktree, "add", "-A")
            if staged.returncode:
                metadata = _metadata(
                    mode=mode, worktree=worktree, branch=branch, command=command,
                    result="rejected", reason="Could not stage Codex lane changes",
                    artifacts=artifacts,
                )
                return json.dumps({"success": True, "metadata": {"codex_lane": metadata}})
            changed = _git(worktree, "diff", "--cached", "--name-only", base_sha).stdout.splitlines()
            forbidden_hit = next((path for path in changed if path in forbidden), None)
            if forbidden_hit:
                metadata = _metadata(mode=mode, worktree=worktree, branch=branch, command=command,
                                     result="rejected", reason=f"Forbidden path changed: {forbidden_hit}", artifacts=artifacts)
            else:
                test_evidence, reason = _run_tests(worktree, tests)
                if reason:
                    metadata = _metadata(mode=mode, worktree=worktree, branch=branch, command=command,
                                         result="rejected", reason=reason, tests=test_evidence, artifacts=artifacts)
                else:
                    patch = _git(worktree, "diff", "--cached", "--binary", base_sha).stdout
                    if not patch.strip():
                        metadata = _metadata(
                            mode=mode, worktree=worktree, branch=branch, command=command,
                            result="rejected", reason="Codex lane produced no changes",
                            tests=test_evidence, artifacts=artifacts,
                        )
                    else:
                        applied = _apply_patch(source, patch)
                        if applied.returncode:
                            metadata = _metadata(
                                mode=mode, worktree=worktree, branch=branch, command=command,
                                result="rejected", reason="Could not reconcile Codex lane diff",
                                tests=test_evidence, artifacts=artifacts,
                            )
                        else:
                            patch_path = _artifact_path(task_id, ".patch")
                            patch_path.write_text(patch, encoding="utf-8")
                            artifacts.append(str(patch_path))
                            commits = _git(worktree, "rev-list", "--reverse", f"{base_sha}..HEAD").stdout.splitlines()
                            metadata = _metadata(
                                mode=mode, worktree=worktree, branch=branch, command=command,
                                result="accepted", commits=commits, tests=test_evidence,
                                artifacts=artifacts,
                            )
                            accepted = True
        return json.dumps({"success": True, "metadata": {"codex_lane": metadata}})
    finally:
        if created:
            _git(source, "worktree", "remove", "--force", str(worktree))
            if accepted:
                _git(source, "branch", "-D", branch)
