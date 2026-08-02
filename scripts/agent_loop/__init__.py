"""Minimal role-based worker/reviewer orchestration prototype."""

from .orchestrator import (
    AdapterError,
    AdapterFailure,
    AdapterFailureKind,
    AgentLoop,
    AgentResult,
    FileStateStore,
    Finding,
    FindingDisposition,
    FindingResponse,
    RoleAdapter,
    RoleConfig,
    RoleSpec,
    Verdict,
    VerdictStatus,
    WorkerResponse,
)
from .adapters import (
    AdapterRouter,
    ClaudeAdapter,
    CodexAdapter,
    OpenCodeAdapter,
    run_subprocess,
)

__all__ = [
    "AdapterError",
    "AdapterFailure",
    "AdapterFailureKind",
    "AgentLoop",
    "AgentResult",
    "FileStateStore",
    "Finding",
    "FindingDisposition",
    "FindingResponse",
    "RoleAdapter",
    "RoleConfig",
    "RoleSpec",
    "Verdict",
    "VerdictStatus",
    "WorkerResponse",
    "AdapterRouter",
    "ClaudeAdapter",
    "CodexAdapter",
    "OpenCodeAdapter",
    "run_subprocess",
]
