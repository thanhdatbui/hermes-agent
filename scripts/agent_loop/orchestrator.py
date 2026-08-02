"""Backend-agnostic worker/reviewer loop with durable phase artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Protocol


class AdapterError(RuntimeError):
    """Base error raised when an adapter cannot satisfy its contract."""


class AdapterFailureKind(str, Enum):
    QUOTA = "quota"
    PROVIDER = "provider"
    TASK = "task"


class AdapterFailure(AdapterError):
    """Classified backend failure; quota/provider failures permit fallback."""

    def __init__(
        self,
        message: str,
        kind: AdapterFailureKind | str = AdapterFailureKind.PROVIDER,
    ) -> None:
        super().__init__(message)
        self.kind = AdapterFailureKind(kind)


class ReviewerUnavailable(AdapterError):
    """All eligible reviewer routes failed."""

    def __init__(self, failures: list[dict[str, str]]) -> None:
        super().__init__("all eligible reviewer routes failed")
        self.failures = failures


class VerdictStatus(str, Enum):
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class FindingDisposition(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


@dataclass(frozen=True)
class Finding:
    finding_id: str
    summary: str
    details: str = ""
    severity: str = "medium"

    def __post_init__(self) -> None:
        if not self.finding_id.strip():
            raise ValueError("finding_id must not be empty")
        if not self.summary.strip():
            raise ValueError("finding summary must not be empty")


@dataclass(frozen=True)
class Verdict:
    status: VerdictStatus
    summary: str
    feedback: str = ""
    findings: tuple[Finding, ...] = ()

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError("verdict summary must not be empty")


@dataclass(frozen=True)
class FindingResponse:
    finding_id: str
    disposition: FindingDisposition
    rationale: str
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.finding_id.strip():
            raise ValueError("finding_id must not be empty")
        if not self.rationale.strip():
            raise ValueError("finding response rationale must not be empty")


@dataclass(frozen=True)
class WorkerResponse:
    responses: tuple[FindingResponse, ...]
    summary: str = ""
    output: Any = None
    output_updated: bool = False


@dataclass(frozen=True)
class RoleSpec:
    """Backend-neutral role route passed unchanged to the configured adapter."""

    name: str
    backend: str = "default"
    options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("role name must not be empty")
        if not self.backend.strip():
            raise ValueError("role backend must not be empty")

    def public_dict(self) -> dict[str, Any]:
        # Persist option names, not values that could contain provider secrets.
        return {
            "name": self.name,
            "backend": self.backend,
            "option_keys": sorted(str(key) for key in self.options),
        }


RoleLike = RoleSpec | str | Mapping[str, Any]


def _coerce_role(value: RoleLike) -> RoleSpec:
    if isinstance(value, RoleSpec):
        return value
    if isinstance(value, str):
        return RoleSpec(value)
    if isinstance(value, Mapping):
        return RoleSpec(
            name=str(value["name"]),
            backend=str(value.get("backend", "default")),
            options=dict(value.get("options", {})),
        )
    raise TypeError(f"invalid role configuration: {value!r}")


@dataclass(frozen=True)
class RoleConfig:
    worker: RoleLike = "worker"
    reviewer: RoleLike = "reviewer"
    fallback_reviewer: RoleLike | None = "fallback_reviewer"
    fallback_reviewers: tuple[RoleLike, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker", _coerce_role(self.worker))
        object.__setattr__(self, "reviewer", _coerce_role(self.reviewer))
        fallback = (
            _coerce_role(self.fallback_reviewer)
            if self.fallback_reviewer is not None
            else None
        )
        object.__setattr__(self, "fallback_reviewer", fallback)
        object.__setattr__(
            self,
            "fallback_reviewers",
            tuple(_coerce_role(role) for role in self.fallback_reviewers),
        )

    def reviewer_chain(self) -> tuple[RoleSpec, ...]:
        configured = [self.reviewer]
        if self.fallback_reviewer is not None:
            configured.append(self.fallback_reviewer)
        configured.extend(self.fallback_reviewers)

        unique: list[RoleSpec] = []
        seen: set[tuple[str, str]] = set()
        for role in configured:
            key = (role.name, role.backend)
            if key not in seen:
                seen.add(key)
                unique.append(role)
        return tuple(unique)

    def public_dict(self) -> dict[str, Any]:
        return {
            "worker": self.worker.public_dict(),
            "reviewers": [role.public_dict() for role in self.reviewer_chain()],
        }


class RoleAdapter(Protocol):
    def run(self, role: RoleSpec, task: str, context: dict[str, Any]) -> Any: ...


class StateStore(Protocol):
    def load(self) -> dict[str, Any] | None: ...

    def save(self, state: dict[str, Any]) -> None: ...

    def write_artifact(self, round_number: int, phase: str, payload: Any) -> str: ...


class FileStateStore:
    """Atomic JSON state plus one durable JSON artifact per completed phase."""

    def __init__(self, path: str | Path):
        path = Path(path)
        if path.suffix.lower() == ".json":
            self.path = path
            self.run_dir = path.parent
        else:
            self.run_dir = path
            self.path = path / "state.json"

    @classmethod
    def for_task(
        cls, task: str, root: str | Path = ".hermes/agent-loop"
    ) -> FileStateStore:
        slug = re.sub(r"[^a-z0-9]+", "-", task.lower()).strip("-")[:48] or "task"
        digest = hashlib.sha256(task.encode("utf-8")).hexdigest()[:8]
        return cls(Path(root) / f"{slug}-{digest}")

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        self._write_json(self.path, state)

    def write_artifact(self, round_number: int, phase: str, payload: Any) -> str:
        path = self.run_dir / "artifacts" / f"round-{round_number:03d}-{phase}.json"
        self._write_json(path, payload)
        return str(path)

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=True, default=str)
                handle.write("\n")
            os.replace(temp_name, path)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise


@dataclass
class AgentResult:
    status: str
    rounds: int
    output: Any = None
    verdict: Verdict | None = None
    reviewer_role: str | None = None
    state: dict[str, Any] = field(default_factory=dict)


class AgentLoop:
    TERMINAL_STATUSES = {"APPROVED", "MAX_ROUNDS", "FINAL_BLOCKED"}

    def __init__(
        self,
        adapter: RoleAdapter,
        state_store: StateStore,
        roles: RoleConfig | None = None,
        max_rounds: int = 3,
    ) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")
        self.adapter = adapter
        self.state_store = state_store
        self.roles = roles or RoleConfig()
        self.max_rounds = max_rounds

    def run(self, task: str) -> AgentResult:
        state = self.state_store.load() or self._new_state(task)
        if state.get("task") != task:
            raise ValueError("state file belongs to a different task")
        if state.get("roles") != self.roles.public_dict():
            raise ValueError("state file belongs to a different role configuration")
        if state.get("status") in self.TERMINAL_STATUSES:
            return self._result_from_state(state)

        previous_consensus: Verdict | None = self._last_consensus(state)
        previous_output = self._last_output(state)
        start_round = len(state["rounds"]) + 1

        for number in range(start_round, self.max_rounds + 1):
            event: dict[str, Any] = {"round": number, "status": "IMPLEMENTING"}
            state["rounds"].append(event)
            state["status"] = "IMPLEMENTING"
            self.state_store.save(state)

            implementation_context = {
                "phase": "implementation",
                "round": number,
                "previous_output": previous_output,
                "previous_consensus": (
                    _verdict_dict(previous_consensus) if previous_consensus else None
                ),
                "feedback": previous_consensus.feedback if previous_consensus else "",
                "role_config": self.roles.worker.public_dict(),
            }
            try:
                output = self.adapter.run(
                    self.roles.worker, task, implementation_context
                )
            except AdapterError as error:
                return self._block(state, event, number, "implementation", error)
            event["implementation"] = self._persist_phase(
                number,
                "implementation",
                {"role": self.roles.worker.public_dict(), "output": output},
            )
            state["status"] = event["status"] = "AUDITING"
            self.state_store.save(state)

            audit_context = {
                "phase": "audit",
                "round": number,
                "worker_output": output,
            }
            try:
                audit_raw, reviewer, audit_failures = self._run_reviewer(
                    task, audit_context
                )
                audit = self._parse_verdict(audit_raw, phase="audit")
            except AdapterError as error:
                return self._block(state, event, number, "audit", error)

            event["audit"] = self._persist_phase(
                number,
                "audit",
                {
                    "reviewer": reviewer.public_dict(),
                    "fallback_used": reviewer != self.roles.reviewer,
                    "failures": audit_failures,
                    "verdict": _verdict_dict(audit),
                },
            )
            state["last_verdict"] = _verdict_dict(audit)
            if audit.status is VerdictStatus.APPROVED:
                return self._approve(state, event, number, output, audit, reviewer)

            state["status"] = event["status"] = "RESPONDING"
            self.state_store.save(state)
            response_context = {
                "phase": "finding_response",
                "round": number,
                "worker_output": output,
                "audit": _verdict_dict(audit),
                "role_config": self.roles.worker.public_dict(),
            }
            try:
                response_raw = self.adapter.run(
                    self.roles.worker, task, response_context
                )
                worker_response = self._parse_worker_response(response_raw, audit)
            except AdapterError as error:
                return self._block(state, event, number, "finding_response", error)

            effective_output = (
                worker_response.output
                if worker_response.output_updated or worker_response.output is not None
                else output
            )
            event["finding_response"] = self._persist_phase(
                number,
                "finding-response",
                {
                    "role": self.roles.worker.public_dict(),
                    "response": _worker_response_dict(worker_response),
                    "effective_output": effective_output,
                },
            )
            state["status"] = event["status"] = "CONSENSUS"
            self.state_store.save(state)

            failed_reviewer_keys = {
                (failure["role"], failure["backend"]) for failure in audit_failures
            }
            consensus_context = {
                "phase": "consensus",
                "round": number,
                "worker_output": effective_output,
                "audit": _verdict_dict(audit),
                "finding_responses": _worker_response_dict(worker_response),
            }
            try:
                consensus_raw, consensus_reviewer, consensus_failures = (
                    self._run_reviewer(
                        task,
                        consensus_context,
                        preferred=reviewer,
                        excluded=failed_reviewer_keys,
                    )
                )
                consensus = self._parse_verdict(
                    consensus_raw,
                    phase="consensus",
                    default_findings=audit.findings,
                )
            except AdapterError as error:
                return self._block(state, event, number, "consensus", error)

            event["consensus"] = self._persist_phase(
                number,
                "consensus",
                {
                    "reviewer": consensus_reviewer.public_dict(),
                    "fallback_used": consensus_reviewer != self.roles.reviewer,
                    "failures": consensus_failures,
                    "verdict": _verdict_dict(consensus),
                },
            )
            state["last_verdict"] = _verdict_dict(consensus)
            if consensus.status is VerdictStatus.APPROVED:
                return self._approve(
                    state,
                    event,
                    number,
                    effective_output,
                    consensus,
                    consensus_reviewer,
                )

            event["status"] = "CHANGES_REQUESTED"
            state["status"] = "CHANGES_REQUESTED"
            self.state_store.save(state)
            previous_consensus = consensus
            previous_output = effective_output

        state["status"] = "MAX_ROUNDS"
        state["stop_reason"] = "MAX_ROUNDS"
        self.state_store.save(state)
        return self._result_from_state(state)

    def _new_state(self, task: str) -> dict[str, Any]:
        state = {
            "version": 1,
            "task": task,
            "status": "RUNNING",
            "max_rounds": self.max_rounds,
            "roles": self.roles.public_dict(),
            "rounds": [],
        }
        self.state_store.save(state)
        return state

    def _run_reviewer(
        self,
        task: str,
        context: dict[str, Any],
        preferred: RoleSpec | None = None,
        excluded: set[tuple[str, str]] | None = None,
    ) -> tuple[Any, RoleSpec, list[dict[str, str]]]:
        excluded = excluded or set()
        chain = list(self.roles.reviewer_chain())
        if preferred is not None:
            chain = [preferred, *(role for role in chain if role != preferred)]

        failures: list[dict[str, str]] = []
        for role in chain:
            key = (role.name, role.backend)
            if key in excluded:
                continue
            role_context = {**context, "role_config": role.public_dict()}
            try:
                return self.adapter.run(role, task, role_context), role, failures
            except AdapterFailure as error:
                if error.kind not in {
                    AdapterFailureKind.QUOTA,
                    AdapterFailureKind.PROVIDER,
                }:
                    raise
                failures.append({
                    "role": role.name,
                    "backend": role.backend,
                    "kind": error.kind.value,
                    "error": str(error),
                })
        raise ReviewerUnavailable(failures)

    def _parse_verdict(
        self,
        response: Any,
        *,
        phase: str,
        default_findings: tuple[Finding, ...] = (),
    ) -> Verdict:
        try:
            if isinstance(response, Verdict):
                verdict = response
            elif isinstance(response, Mapping):
                findings = tuple(
                    _parse_finding(item) for item in response.get("findings", ())
                )
                verdict = Verdict(
                    VerdictStatus(response["status"]),
                    str(response["summary"]),
                    str(response.get("feedback", "")),
                    findings,
                )
            else:
                raise TypeError("response is not a Verdict or mapping")
        except (KeyError, TypeError, ValueError) as error:
            raise AdapterError(f"invalid {phase} verdict: {error}") from error

        if verdict.status is VerdictStatus.APPROVED and verdict.findings:
            raise AdapterError(
                f"invalid {phase} verdict: approved verdict has findings"
            )
        if verdict.status is VerdictStatus.CHANGES_REQUESTED and not verdict.findings:
            findings = default_findings or (
                Finding("finding-1", verdict.summary, verdict.feedback),
            )
            verdict = Verdict(
                verdict.status, verdict.summary, verdict.feedback, tuple(findings)
            )
        return verdict

    def _parse_worker_response(self, response: Any, audit: Verdict) -> WorkerResponse:
        try:
            if isinstance(response, WorkerResponse):
                parsed = response
            elif isinstance(response, Mapping):
                items = []
                for item in response.get("responses", ()):
                    items.append(
                        FindingResponse(
                            finding_id=str(item["finding_id"]),
                            disposition=FindingDisposition(item["disposition"]),
                            rationale=str(item["rationale"]),
                            evidence=tuple(
                                str(value) for value in item.get("evidence", ())
                            ),
                        )
                    )
                parsed = WorkerResponse(
                    responses=tuple(items),
                    summary=str(response.get("summary", "")),
                    output=response.get("output"),
                    output_updated="output" in response,
                )
            else:
                raise TypeError("response is not a WorkerResponse or mapping")
        except (KeyError, TypeError, ValueError) as error:
            raise AdapterError(f"invalid worker finding response: {error}") from error

        expected = [finding.finding_id for finding in audit.findings]
        actual = [item.finding_id for item in parsed.responses]
        if len(actual) != len(set(actual)):
            raise AdapterError("worker returned duplicate finding responses")
        if set(actual) != set(expected):
            raise AdapterError(
                "worker must respond exactly once to every review finding"
            )
        return parsed

    def _persist_phase(
        self, round_number: int, phase: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        artifact = self.state_store.write_artifact(round_number, phase, payload)
        return {**payload, "artifact": artifact}

    def _approve(
        self,
        state: dict[str, Any],
        event: dict[str, Any],
        number: int,
        output: Any,
        verdict: Verdict,
        reviewer: RoleSpec,
    ) -> AgentResult:
        event["status"] = "APPROVED"
        state["status"] = "APPROVED"
        state["last_verdict"] = _verdict_dict(verdict)
        self.state_store.save(state)
        return AgentResult("APPROVED", number, output, verdict, reviewer.name, state)

    def _block(
        self,
        state: dict[str, Any],
        event: dict[str, Any],
        number: int,
        phase: str,
        error: AdapterError,
    ) -> AgentResult:
        if isinstance(error, ReviewerUnavailable):
            details: dict[str, Any] = {
                "type": type(error).__name__,
                "message": str(error),
                "failures": error.failures,
            }
        elif isinstance(error, AdapterFailure):
            details = {
                "type": type(error).__name__,
                "kind": error.kind.value,
                "message": str(error),
            }
        else:
            details = {"type": type(error).__name__, "message": str(error)}
        event["error"] = self._persist_phase(
            number, f"{phase}-error", {"phase": phase, "error": details}
        )
        event["status"] = "FINAL_BLOCKED"
        state["status"] = "FINAL_BLOCKED"
        state["stop_reason"] = phase
        self.state_store.save(state)
        return AgentResult("FINAL_BLOCKED", number, state=state)

    def _result_from_state(self, state: dict[str, Any]) -> AgentResult:
        rounds = len(state.get("rounds", []))
        verdict = None
        raw_verdict = state.get("last_verdict")
        if raw_verdict:
            verdict = self._parse_verdict(
                raw_verdict,
                phase="stored",
                default_findings=tuple(
                    _parse_finding(item) for item in raw_verdict.get("findings", ())
                ),
            )
        reviewer_role = None
        if state.get("rounds"):
            last = state["rounds"][-1]
            phase = last.get("consensus") or last.get("audit") or {}
            reviewer_role = (phase.get("reviewer") or {}).get("name")
        return AgentResult(
            state["status"],
            rounds,
            self._last_output(state),
            verdict,
            reviewer_role,
            state,
        )

    @staticmethod
    def _last_output(state: dict[str, Any]) -> Any:
        if not state.get("rounds"):
            return None
        event = state["rounds"][-1]
        response = event.get("finding_response") or {}
        if "effective_output" in response:
            return response["effective_output"]
        return (event.get("implementation") or {}).get("output")

    def _last_consensus(self, state: dict[str, Any]) -> Verdict | None:
        if not state.get("rounds"):
            return None
        raw = (state["rounds"][-1].get("consensus") or {}).get("verdict")
        if not raw:
            return None
        return self._parse_verdict(raw, phase="stored consensus")


def _parse_finding(value: Finding | Mapping[str, Any]) -> Finding:
    if isinstance(value, Finding):
        return value
    return Finding(
        finding_id=str(value.get("finding_id", value.get("id", ""))),
        summary=str(value["summary"]),
        details=str(value.get("details", "")),
        severity=str(value.get("severity", "medium")),
    )


def _finding_dict(finding: Finding) -> dict[str, Any]:
    return {
        "finding_id": finding.finding_id,
        "summary": finding.summary,
        "details": finding.details,
        "severity": finding.severity,
    }


def _verdict_dict(verdict: Verdict) -> dict[str, Any]:
    return {
        "status": verdict.status.value,
        "summary": verdict.summary,
        "feedback": verdict.feedback,
        "findings": [_finding_dict(finding) for finding in verdict.findings],
    }


def _worker_response_dict(response: WorkerResponse) -> dict[str, Any]:
    payload = {
        "summary": response.summary,
        "responses": [
            {
                "finding_id": item.finding_id,
                "disposition": item.disposition.value,
                "rationale": item.rationale,
                "evidence": list(item.evidence),
            }
            for item in response.responses
        ],
        "output_updated": response.output_updated or response.output is not None,
    }
    if payload["output_updated"]:
        payload["output"] = response.output
    return payload
