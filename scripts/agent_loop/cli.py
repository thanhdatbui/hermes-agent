"""CLI for the agent loop, with deterministic demo and real subprocess modes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    # Allow ``python <hermes-repo>/scripts/agent_loop/cli.py`` from any cwd.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from .adapters import AdapterRouter, ClaudeAdapter, CodexAdapter, OpenCodeAdapter
    from .orchestrator import AgentLoop, FileStateStore, RoleConfig, Verdict, VerdictStatus
except ImportError:  # direct execution from a target repository
    from scripts.agent_loop.adapters import (
        AdapterRouter,
        ClaudeAdapter,
        CodexAdapter,
        OpenCodeAdapter,
    )
    from scripts.agent_loop.orchestrator import (
        AgentLoop,
        FileStateStore,
        RoleConfig,
        Verdict,
        VerdictStatus,
    )


class DemoAdapter:
    def run(self, role, task, context):
        if context["phase"] == "implementation":
            return {"task": task, "round": context["round"], "draft": "demo output"}
        return Verdict(VerdictStatus.APPROVED, f"{role.name} approved demo output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Chạy agent loop worker/reviewer ở demo hoặc backend CLI thật."
    )
    parser.add_argument("task")
    parser.add_argument("--state")
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument(
        "--demo", action="store_true", help="Dùng adapter deterministic"
    )
    parser.add_argument("--cwd", default=".", help="Workspace truyền cho các backend")
    parser.add_argument(
        "--state-root",
        help="Thư mục state; mặc định là <cwd>/.hermes/agent-loop",
    )
    parser.add_argument("--timeout", type=float, default=None)

    parser.add_argument(
        "--backend",
        help="Backend mặc định cho mọi role; backend riêng có độ ưu tiên cao hơn",
    )
    parser.add_argument("--worker-backend")
    parser.add_argument("--reviewer-backend")
    parser.add_argument("--fallback-backend")

    parser.add_argument("--model", help="Model mặc định cho mọi role")
    parser.add_argument("--worker-model")
    parser.add_argument("--reviewer-model")
    parser.add_argument("--fallback-model")
    parser.add_argument("--effort", help="Effort mặc định cho mọi role")
    parser.add_argument("--worker-effort")
    parser.add_argument("--reviewer-effort")
    parser.add_argument("--fallback-effort")

    parser.add_argument("--worker-role", default="worker")
    parser.add_argument("--reviewer-role", default="reviewer")
    parser.add_argument("--fallback-role", default="fallback_reviewer")
    return parser


def _first(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is not None:
            return value
    return default


def _role_options(
    *,
    model: str | None,
    effort: str | None,
) -> dict[str, str]:
    options: dict[str, str] = {}
    if model:
        options["model"] = model
    if effort:
        options["effort"] = effort
    return options


def roles_from_args(args: argparse.Namespace) -> RoleConfig:
    backend = args.backend
    worker_backend = _first(args.worker_backend, backend, default="codex")
    reviewer_backend = _first(args.reviewer_backend, backend, default="claude")
    fallback_backend = _first(args.fallback_backend, backend, default="opencode")

    worker_model = _first(
        args.worker_model,
        args.model,
        default="gpt-5.6-luna" if worker_backend == "codex" else None,
    )
    reviewer_model = _first(
        args.reviewer_model,
        args.model,
        default="opus" if reviewer_backend == "claude" else None,
    )
    fallback_model = _first(
        args.fallback_model, args.reviewer_model, args.model, default=None
    )
    worker_effort = _first(args.worker_effort, args.effort, default="high")
    reviewer_effort = _first(args.reviewer_effort, args.effort, default="low")
    fallback_effort = _first(
        args.fallback_effort, args.reviewer_effort, args.effort, default=None
    )

    return RoleConfig(
        worker={
            "name": args.worker_role,
            "backend": worker_backend,
            "options": _role_options(model=worker_model, effort=worker_effort),
        },
        reviewer={
            "name": args.reviewer_role,
            "backend": reviewer_backend,
            "options": _role_options(model=reviewer_model, effort=reviewer_effort),
        },
        fallback_reviewer={
            "name": args.fallback_role,
            "backend": fallback_backend,
            "options": _role_options(model=fallback_model, effort=fallback_effort),
        },
    )


def adapter_from_args(args: argparse.Namespace) -> AdapterRouter:
    cwd = Path(args.cwd).resolve()
    adapters = {
        "codex": CodexAdapter(cwd=cwd, timeout=args.timeout),
        "claude": ClaudeAdapter(cwd=cwd, timeout=args.timeout),
        "opencode": OpenCodeAdapter(cwd=cwd, timeout=args.timeout),
    }
    return AdapterRouter(adapters)


def configured_roles_from_args(args: argparse.Namespace) -> RoleConfig:
    if args.demo:
        return RoleConfig(args.worker_role, args.reviewer_role, args.fallback_role)
    return roles_from_args(args)


def main() -> int:
    args = build_parser().parse_args()
    roles = configured_roles_from_args(args)
    workspace = Path(args.cwd).resolve()
    store = (
        FileStateStore(args.state) if args.state else FileStateStore.for_task(args.task)
    )
    if not args.state:
        state_root = Path(args.state_root).resolve() if args.state_root else workspace / ".hermes/agent-loop"
        store = FileStateStore.for_task(args.task, root=state_root)
    adapter = DemoAdapter() if args.demo else adapter_from_args(args)
    result = AgentLoop(adapter, store, roles, args.max_rounds).run(args.task)
    print(result.status)
    return 0 if result.status == "APPROVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
