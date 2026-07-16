"""Safe, portable Claude Code input lane for Kanban workers."""

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


def _config() -> dict[str, Any]:
    cfg = load_config() or {}
    lane = ((cfg.get("kanban") or {}).get("external_lanes") or {}).get("claude")
    return lane if isinstance(lane, dict) else {}


def check_claude_lane() -> bool:
    return bool(os.getenv("HERMES_KANBAN_TASK")) and bool(_config().get("enabled", False))


def _safe_task(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-") or "task"


def build_branch_name(task_id: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"claude/{_safe_task(task_id)}/{stamp}"


def build_worktree_path(task_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"hermes-claude-{_safe_task(task_id)}-{uuid.uuid4().hex[:8]}"


def _run(argv: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False,
                          env=_sanitize_subprocess_env(os.environ), encoding="utf-8", errors="replace")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=repo)


def _apply_patch(repo: Path, patch: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"], cwd=repo, input=patch,
        text=True, capture_output=True, check=False,
        env=_sanitize_subprocess_env(os.environ), encoding="utf-8", errors="replace",
    )


def _artifact_path(task_id: str, suffix: str) -> Path:
    root = get_hermes_home() / "artifacts" / "external-lanes" / _safe_task(task_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"claude-{uuid.uuid4().hex[:12]}{suffix}"


def _parse_result(output: str) -> dict[str, Any]:
    try:
        parsed = json.loads(output)
    except (TypeError, ValueError) as exc:
        raise ValueError("Claude output was not valid JSON") from exc
    if not isinstance(parsed, dict) or parsed.get("type") != "result":
        raise ValueError("Claude JSON result envelope is invalid")
    return {
        "usage": parsed.get("usage") if isinstance(parsed.get("usage"), dict) else {},
        "cost_usd": parsed.get("total_cost_usd"),
        "session_id": parsed.get("session_id"),
        "model_usage": parsed.get("modelUsage") if isinstance(parsed.get("modelUsage"), dict) else {},
    }


def _metadata(*, worktree: Path | None, branch: str | None, command: str | None,
              result: str, reason: str = "", tests: list[dict[str, Any]] | None = None,
              commits: list[str] | None = None, parsed: dict[str, Any] | None = None,
              artifacts: list[str] | None = None) -> dict[str, Any]:
    data = {
        "used": worktree is not None, "worktree": str(worktree) if worktree else None,
        "branch": branch, "command": command, "result": result,
        "accepted_commits": commits or [], "rejected_reason": reason,
        "tests_run": tests or [], "artifacts": artifacts or [], "usage": {}, "cost_usd": None,
        "session_id": None, "model_usage": {},
    }
    if parsed:
        data.update(parsed)
    if result not in {"accepted", "rejected", "timed_out"}:
        raise ValueError("invalid Claude lane result")
    return data


def _run_tests(worktree: Path, commands: list[str]) -> tuple[list[dict[str, Any]], str]:
    evidence: list[dict[str, Any]] = []
    for command in commands:
        done = subprocess.run(command, cwd=worktree, shell=True, text=True, capture_output=True,
                              check=False, env=_sanitize_subprocess_env(os.environ), encoding="utf-8", errors="replace")
        evidence.append({"command": command, "exit_code": done.returncode, "owner": "hermes"})
        if done.returncode:
            return evidence, f"Hermes verification failed: {command}"
    return evidence, ""


def run_claude_lane(args: dict[str, Any], task_id: str | None = None, **_: Any) -> str:
    if not check_claude_lane():
        return tool_error("Claude lane is disabled or this is not a Kanban worker")
    cfg, task_id = _config(), task_id or os.getenv("HERMES_KANBAN_TASK", "")
    executable = str(cfg.get("executable") or "claude")
    resolved = shutil.which(executable)
    if not resolved:
        return tool_error("Claude executable is unavailable", executable=executable)
    source = Path(str(args.get("workspace") or "")).expanduser().resolve()
    if not source.is_dir() or _git(source, "rev-parse", "--is-inside-work-tree").returncode:
        return tool_error("workspace must be an existing git worktree")
    if _git(source, "status", "--porcelain").stdout.strip():
        return tool_error(
            "workspace must be clean before starting a Claude lane; "
            "resolve the existing diff instead of retrying"
        )
    base_sha = _git(source, "rev-parse", "HEAD").stdout.strip()
    if _run([resolved, "--version"], cwd=source).returncode:
        return tool_error("Claude capability check failed", executable=executable)
    allowed = cfg.get("allowed_tools") or []
    if not isinstance(allowed, list) or not all(isinstance(item, str) and item for item in allowed):
        return tool_error("Claude allowed_tools must be a non-empty string list")
    branch, worktree = build_branch_name(task_id), build_worktree_path(task_id)
    command = " ".join([
        shlex.quote(resolved), "-p", "--output-format", "json", "--permission-mode", "default",
        "--max-turns", str(max(1, int(cfg.get("max_turns") or 10))), "--allowedTools",
        shlex.quote(",".join(allowed)), shlex.quote(str(args["prompt"])),
    ])
    timeout = max(1, int(cfg.get("timeout_seconds") or 300))
    forbidden = {str(item) for item in args.get("forbidden_paths") or []}
    tests = [str(item) for item in args.get("test_commands") or []]
    artifacts: list[str] = []
    created = accepted = False
    try:
        if _git(source, "worktree", "add", "-b", branch, str(worktree), "HEAD").returncode:
            return tool_error("Could not create isolated Claude worktree")
        created = True
        session = process_registry.spawn_local(command, cwd=str(worktree), task_id=task_id, use_pty=False)
        waited = process_registry.wait(session.id, timeout=timeout)
        output_path = _artifact_path(task_id, ".log")
        output_path.write_text(str(waited.get("output") or ""), encoding="utf-8")
        artifacts.append(str(output_path))
        if waited["status"] == "timeout":
            process_registry.kill_process(session.id, source="kanban_claude_lane.timeout")
            meta = _metadata(worktree=worktree, branch=branch, command=command, result="timed_out", reason="Claude lane timeout", artifacts=artifacts)
        elif waited["status"] != "exited" or waited.get("exit_code") != 0:
            meta = _metadata(worktree=worktree, branch=branch, command=command, result="rejected", reason="Claude CLI exited unsuccessfully", artifacts=artifacts)
        else:
            try:
                parsed = _parse_result(str(waited.get("output") or ""))
            except ValueError as exc:
                meta = _metadata(worktree=worktree, branch=branch, command=command, result="rejected", reason=str(exc), artifacts=artifacts)
            else:
                staged = _git(worktree, "add", "-A")
                if staged.returncode:
                    meta = _metadata(worktree=worktree, branch=branch, command=command, result="rejected", reason="Could not stage Claude lane changes", parsed=parsed, artifacts=artifacts)
                    return json.dumps({"success": True, "metadata": {"claude_lane": meta}})
                changed = _git(worktree, "diff", "--cached", "--name-only", base_sha).stdout.splitlines()
                hit = next((path for path in changed if path in forbidden), None)
                test_evidence, reason = _run_tests(worktree, tests) if not hit else ([], f"Forbidden path changed: {hit}")
                if reason:
                    meta = _metadata(worktree=worktree, branch=branch, command=command, result="rejected", reason=reason, tests=test_evidence, parsed=parsed, artifacts=artifacts)
                else:
                    patch = _git(worktree, "diff", "--cached", "--binary", base_sha).stdout
                    if not patch.strip():
                        meta = _metadata(worktree=worktree, branch=branch, command=command, result="rejected", reason="Claude lane produced no changes", tests=test_evidence, parsed=parsed, artifacts=artifacts)
                    else:
                        applied = _apply_patch(source, patch)
                        if applied.returncode:
                            meta = _metadata(worktree=worktree, branch=branch, command=command, result="rejected", reason="Could not reconcile Claude lane diff", tests=test_evidence, parsed=parsed, artifacts=artifacts)
                        else:
                            patch_path = _artifact_path(task_id, ".patch")
                            patch_path.write_text(patch, encoding="utf-8")
                            artifacts.append(str(patch_path))
                            commits = _git(worktree, "rev-list", "--reverse", f"{base_sha}..HEAD").stdout.splitlines()
                            meta = _metadata(worktree=worktree, branch=branch, command=command, result="accepted", tests=test_evidence, commits=commits, parsed=parsed, artifacts=artifacts)
                            accepted = True
        return json.dumps({"success": True, "metadata": {"claude_lane": meta}})
    finally:
        if created:
            _git(source, "worktree", "remove", "--force", str(worktree))
            if accepted:
                _git(source, "branch", "-D", branch)
