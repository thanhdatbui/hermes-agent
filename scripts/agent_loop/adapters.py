"""Subprocess adapters for real worker/reviewer CLI backends."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .orchestrator import (
    AdapterError,
    AdapterFailure,
    AdapterFailureKind,
    Finding,
    FindingDisposition,
    FindingResponse,
    RoleSpec,
    Verdict,
    VerdictStatus,
    WorkerResponse,
)


SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


_QUOTA_PATTERNS = (
    "quota",
    "rate limit",
    "rate_limit",
    "usage limit",
    "credit balance",
    "credits exhausted",
    "insufficient credits",
    "too many requests",
    "resource_exhausted",
    "limit reached",
    "hit your limit",
    "http 429",
    "status code 429",
)
_PROVIDER_PATTERNS = (
    "provider",
    "overloaded",
    "service unavailable",
    "temporarily unavailable",
    "authentication",
    "unauthorized",
    "invalid api key",
    "invalid token",
    "connection refused",
    "connection reset",
    "econnrefused",
    "econnreset",
    "network error",
    "timed out",
    "timeout",
    "not found",
    "enoent",
)


def run_subprocess(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one backend command without invoking a shell."""

    resolved_command = _resolve_command(command)
    return subprocess.run(
        resolved_command,
        input=input_text,
        cwd=str(cwd) if cwd is not None else None,
        timeout=timeout,
        check=False,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _resolve_command(command: Sequence[str]) -> list[str]:
    """Resolve executable shims while keeping shell=False for prompt safety."""

    resolved = shutil.which(command[0])
    if not resolved:
        return list(command)
    path = Path(resolved)
    if path.suffix.lower() not in {".cmd", ".bat"}:
        return [resolved, *command[1:]]

    try:
        shim = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return list(command)
    match = re.search(
        r'"(?P<target>(?:%dp0%|%~dp0)[^"]+\.exe)"\s+%\*',
        shim,
        re.IGNORECASE,
    )
    if not match:
        return list(command)
    target = re.sub(
        r"^%~?dp0%",
        lambda _: str(path.parent) + "\\",
        match.group("target"),
    )
    target_path = Path(target).resolve()
    if not target_path.exists():
        return list(command)
    return [str(target_path), *command[1:]]


class AdapterRouter:
    """Dispatch role calls to adapters keyed by backend name."""

    def __init__(self, adapters: Mapping[str, Any]) -> None:
        self.adapters = {name.lower(): adapter for name, adapter in adapters.items()}

    def run(self, role: RoleSpec, task: str, context: dict[str, Any]) -> Any:
        adapter = self.adapters.get(role.backend.lower())
        if adapter is None:
            raise AdapterFailure(
                f"backend không được cấu hình: {role.backend}",
                AdapterFailureKind.PROVIDER,
            )
        return adapter.run(role, task, context)


class _SubprocessAdapter:
    backend_name = "subprocess"

    def __init__(
        self,
        *,
        executable: str,
        cwd: str | Path | None = None,
        timeout: float | None = None,
        runner: SubprocessRunner = run_subprocess,
    ) -> None:
        self.executable = executable
        self.cwd = Path(cwd or Path.cwd()).resolve()
        self.timeout = timeout
        self.runner = runner

    def run(self, role: RoleSpec, task: str, context: dict[str, Any]) -> Any:
        phase = str(context.get("phase", ""))
        if phase not in {"implementation", "finding_response", "audit", "consensus"}:
            raise AdapterError(f"phase không được hỗ trợ: {phase!r}")

        prompt = _build_prompt(role, task, context)
        command, input_text = self.build_command(role, phase, prompt)
        try:
            completed = self.runner(
                command,
                input_text=input_text,
                cwd=self.cwd,
                timeout=self.timeout,
            )
        except FileNotFoundError as error:
            raise AdapterFailure(
                f"không tìm thấy CLI {self.executable}: {error}",
                AdapterFailureKind.PROVIDER,
            ) from error
        except subprocess.TimeoutExpired as error:
            raise AdapterFailure(
                f"CLI {self.backend_name} hết thời gian sau {self.timeout} giây",
                AdapterFailureKind.PROVIDER,
            ) from error
        except OSError as error:
            raise AdapterFailure(
                f"không thể chạy CLI {self.backend_name}: {error}",
                AdapterFailureKind.PROVIDER,
            ) from error

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if completed.returncode != 0:
            detail = _failure_detail(stdout, stderr, completed.returncode)
            raise AdapterFailure(detail, _classify_failure(detail))

        reported_error = _reported_error(stdout)
        if reported_error:
            raise AdapterFailure(reported_error, _classify_failure(reported_error))
        try:
            payload = _decode_output(stdout, phase=phase, backend=self.backend_name)
        except AdapterError as error:
            detail = "\n".join(part for part in (stdout, stderr) if part).strip()
            kind = _classify_failure(detail)
            if kind is not AdapterFailureKind.TASK:
                raise AdapterFailure(detail or str(error), kind) from error
            raise
        return _parse_phase_payload(payload, phase)

    def build_command(
        self, role: RoleSpec, phase: str, prompt: str
    ) -> tuple[list[str], str | None]:
        raise NotImplementedError


class CodexAdapter(_SubprocessAdapter):
    backend_name = "codex"

    def __init__(
        self,
        *,
        executable: str = "codex",
        cwd: str | Path | None = None,
        timeout: float | None = None,
        runner: SubprocessRunner = run_subprocess,
    ) -> None:
        super().__init__(executable=executable, cwd=cwd, timeout=timeout, runner=runner)

    def build_command(
        self, role: RoleSpec, phase: str, prompt: str
    ) -> tuple[list[str], str | None]:
        reviewer = phase in {"audit", "consensus"}
        command = [
            self.executable,
            "exec",
            "--ephemeral",
            "--color",
            "never",
            "--json",
            "--sandbox",
            "read-only" if reviewer else "workspace-write",
            "--cd",
            str(self.cwd),
        ]
        model = role.options.get("model")
        effort = role.options.get("effort")
        if model:
            command.extend(["--model", str(model)])
        if effort:
            command.extend(["--config", f'model_reasoning_effort="{effort}"'])
        command.append("-")
        return command, prompt


class ClaudeAdapter(_SubprocessAdapter):
    backend_name = "claude"

    def __init__(
        self,
        *,
        executable: str = "claude",
        cwd: str | Path | None = None,
        timeout: float | None = None,
        runner: SubprocessRunner = run_subprocess,
    ) -> None:
        super().__init__(executable=executable, cwd=cwd, timeout=timeout, runner=runner)

    def build_command(
        self, role: RoleSpec, phase: str, prompt: str
    ) -> tuple[list[str], str | None]:
        reviewer = phase in {"audit", "consensus"}
        command = [
            self.executable,
            "--print",
            "--output-format",
            "json",
            "--no-session-persistence",
            "--json-schema",
            json.dumps(_schema_for_phase(phase), separators=(",", ":")),
            "--permission-mode",
            "plan" if reviewer else "acceptEdits",
        ]
        if reviewer:
            command.extend(["--tools", "Read,Grep,Glob"])
        model = role.options.get("model")
        effort = role.options.get("effort")
        if model:
            command.extend(["--model", str(model)])
        if effort:
            command.extend(["--effort", str(effort)])
        return command, prompt


class OpenCodeAdapter(_SubprocessAdapter):
    backend_name = "opencode"

    def __init__(
        self,
        *,
        executable: str = "opencode",
        cwd: str | Path | None = None,
        timeout: float | None = None,
        runner: SubprocessRunner = run_subprocess,
    ) -> None:
        super().__init__(executable=executable, cwd=cwd, timeout=timeout, runner=runner)

    def build_command(
        self, role: RoleSpec, phase: str, prompt: str
    ) -> tuple[list[str], str | None]:
        reviewer = phase in {"audit", "consensus"}
        command = [
            self.executable,
            "run",
            "--format",
            "json",
            "--dir",
            str(self.cwd),
            "--agent",
            "plan" if reviewer else "build",
        ]
        model = role.options.get("model")
        effort = role.options.get("effort")
        if model:
            command.extend(["--model", str(model)])
        if effort:
            command.extend(["--variant", str(effort)])
        command.append(prompt)
        return command, None


def _build_prompt(role: RoleSpec, task: str, context: Mapping[str, Any]) -> str:
    phase = str(context["phase"])
    contracts = {
        "implementation": (
            "Thực hiện task trong workspace. Trả về JSON có `output` là báo cáo "
            "implementation có thể dùng cho reviewer và `summary` ngắn."
        ),
        "finding_response": (
            "Xử lý từng finding. Trả về JSON có `responses`; mỗi finding đúng một "
            "phản hồi gồm finding_id, disposition ACCEPT/REJECT, rationale, evidence. "
            "Nếu implementation thay đổi, thêm `output`."
        ),
        "audit": (
            "Chỉ đọc và review implementation. Không sửa file. Trả về Verdict JSON "
            "với status APPROVED hoặc CHANGES_REQUESTED, summary, feedback, findings."
        ),
        "consensus": (
            "Chỉ đọc và đánh giá lại findings cùng phản hồi worker. Không sửa file. "
            "Trả về Verdict JSON với status APPROVED hoặc CHANGES_REQUESTED."
        ),
    }
    envelope = {
        "phase": phase,
        "task": task,
        "context": context,
        "role": {
            "name": role.name,
            "backend": role.backend,
            "options": _safe_role_options(role.options),
        },
    }
    return (
        "Bạn là một role trong agent loop độc lập. "
        + contracts[phase]
        + " Chỉ xuất một JSON object đúng schema, không bọc Markdown.\n\n"
        + json.dumps(envelope, ensure_ascii=False, default=str, indent=2)
    )


def _safe_role_options(options: Mapping[str, Any]) -> dict[str, Any]:
    sensitive_markers = (
        "secret",
        "token",
        "password",
        "apikey",
        "key",
        "credential",
        "privatekey",
    )
    safe: dict[str, Any] = {}
    for key, value in options.items():
        normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
        if any(marker in normalized for marker in sensitive_markers):
            continue
        safe[str(key)] = value
    return safe


def _schema_for_phase(phase: str) -> dict[str, Any]:
    if phase == "implementation":
        return {
            "type": "object",
            "properties": {"output": {}, "summary": {"type": "string"}},
            "required": ["output"],
            "additionalProperties": True,
        }
    if phase == "finding_response":
        return {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "responses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "finding_id": {"type": "string"},
                            "disposition": {"enum": ["ACCEPT", "REJECT"]},
                            "rationale": {"type": "string"},
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["finding_id", "disposition", "rationale"],
                        "additionalProperties": False,
                    },
                },
                "output": {},
            },
            "required": ["responses"],
            "additionalProperties": False,
        }
    return {
        "type": "object",
        "properties": {
            "status": {"enum": ["APPROVED", "CHANGES_REQUESTED"]},
            "summary": {"type": "string"},
            "feedback": {"type": "string"},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "finding_id": {"type": "string"},
                        "summary": {"type": "string"},
                        "details": {"type": "string"},
                        "severity": {"type": "string"},
                    },
                    "required": ["finding_id", "summary"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["status", "summary", "findings"],
        "additionalProperties": False,
    }


def _decode_output(stdout: str, *, phase: str, backend: str) -> Any:
    text = stdout.strip()
    if not text:
        raise AdapterError(f"CLI {backend} không trả về output")

    values: list[Any] = []
    try:
        values.append(json.loads(text))
    except json.JSONDecodeError:
        for line in text.splitlines():
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    for value in reversed(values):
        payload = _find_contract_payload(value, phase)
        if payload is not None:
            return payload

    fragments: list[str] = []
    for value in values:
        fragments.extend(_event_text_fragments(value))
    if fragments:
        for candidate in ("".join(fragments), "\n".join(fragments)):
            parsed = _json_from_text(candidate)
            payload = _find_contract_payload(parsed, phase)
            if payload is not None:
                return payload

    parsed = _json_from_text(text)
    payload = _find_contract_payload(parsed, phase)
    if payload is not None:
        return payload
    raise AdapterError(f"output {backend} không chứa JSON hợp lệ cho phase {phase}")


def _find_contract_payload(value: Any, phase: str) -> Any | None:
    if isinstance(value, Mapping):
        if _matches_phase(value, phase):
            return value
        structured = value.get("structured_output")
        if structured is not None:
            if isinstance(structured, str):
                structured = _json_from_text(structured)
            found = _find_contract_payload(structured, phase)
            if found is not None:
                return found
        for key in ("result", "message", "content", "output", "data", "part", "item"):
            nested = value.get(key)
            if nested is None:
                continue
            if isinstance(nested, str):
                nested = _json_from_text(nested)
            found = _find_contract_payload(nested, phase)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in reversed(value):
            found = _find_contract_payload(item, phase)
            if found is not None:
                return found
    return None


def _matches_phase(value: Mapping[str, Any], phase: str) -> bool:
    if phase == "implementation":
        return "output" in value
    if phase == "finding_response":
        return "responses" in value
    return "status" in value and "summary" in value


def _event_text_fragments(value: Any) -> list[str]:
    fragments: list[str] = []
    if isinstance(value, Mapping):
        item = value.get("item")
        if isinstance(item, Mapping) and item.get("type") == "agent_message":
            if isinstance(item.get("text"), str):
                fragments.append(item["text"])
        part = value.get("part")
        if isinstance(part, Mapping) and isinstance(part.get("text"), str):
            fragments.append(part["text"])
        if value.get("type") in {"text", "assistant", "message"}:
            for key in ("text", "content"):
                if isinstance(value.get(key), str):
                    fragments.append(value[key])
    return fragments


def _json_from_text(text: str) -> Any | None:
    candidate = text.strip()
    if not candidate:
        return None
    fenced = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for match in re.finditer(r"[\[{]", candidate):
            try:
                return decoder.raw_decode(candidate[match.start() :])[0]
            except json.JSONDecodeError:
                continue
    return None


def _parse_phase_payload(payload: Any, phase: str) -> Any:
    try:
        if phase == "implementation":
            if not isinstance(payload, Mapping) or "output" not in payload:
                raise TypeError("implementation phải có trường output")
            return payload["output"]
        if phase == "finding_response":
            if not isinstance(payload, Mapping):
                raise TypeError("finding response phải là object")
            responses = tuple(
                FindingResponse(
                    finding_id=str(item["finding_id"]),
                    disposition=FindingDisposition(item["disposition"]),
                    rationale=str(item["rationale"]),
                    evidence=tuple(str(entry) for entry in item.get("evidence", ())),
                )
                for item in payload.get("responses", ())
            )
            return WorkerResponse(
                responses=responses,
                summary=str(payload.get("summary", "")),
                output=payload.get("output"),
                output_updated="output" in payload,
            )
        if not isinstance(payload, Mapping):
            raise TypeError("verdict phải là object")
        findings = tuple(
            Finding(
                finding_id=str(item.get("finding_id", item.get("id", ""))),
                summary=str(item["summary"]),
                details=str(item.get("details", "")),
                severity=str(item.get("severity", "medium")),
            )
            for item in payload.get("findings", ())
        )
        return Verdict(
            status=VerdictStatus(payload["status"]),
            summary=str(payload["summary"]),
            feedback=str(payload.get("feedback", "")),
            findings=findings,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise AdapterError(f"JSON không hợp lệ cho phase {phase}: {error}") from error


def _classify_failure(message: str) -> AdapterFailureKind:
    lowered = message.lower()
    if any(pattern in lowered for pattern in _QUOTA_PATTERNS):
        return AdapterFailureKind.QUOTA
    if any(pattern in lowered for pattern in _PROVIDER_PATTERNS):
        return AdapterFailureKind.PROVIDER
    return AdapterFailureKind.TASK


def _reported_error(stdout: str) -> str | None:
    values: list[Any] = []
    try:
        values.append(json.loads(stdout))
    except json.JSONDecodeError:
        for line in stdout.splitlines():
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    for value in values:
        if not isinstance(value, Mapping):
            continue
        event_type = str(value.get("type", "")).lower()
        if value.get("is_error") is True or event_type in {
            "error",
            "turn.failed",
            "session.error",
        }:
            detail = value.get("error") or value.get("result") or value.get("message")
            if isinstance(detail, str):
                return detail
            if detail is not None:
                return json.dumps(detail, ensure_ascii=False, default=str)
            return json.dumps(value, ensure_ascii=False, default=str)
    return None


def _failure_detail(stdout: str, stderr: str, returncode: int) -> str:
    detail = "\n".join(part.strip() for part in (stderr, stdout) if part.strip())
    return detail or f"CLI thoát với mã {returncode}"
