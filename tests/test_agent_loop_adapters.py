import subprocess

import pytest

from scripts.agent_loop import adapters as adapter_module
from scripts.agent_loop import (
    AdapterFailure,
    AdapterFailureKind,
    ClaudeAdapter,
    CodexAdapter,
    FindingDisposition,
    OpenCodeAdapter,
    RoleSpec,
    VerdictStatus,
    WorkerResponse,
)
from scripts.agent_loop.cli import (
    build_parser,
    configured_roles_from_args,
    roles_from_args,
)


class MockRunner:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((list(command), kwargs))
        return subprocess.CompletedProcess(
            command, self.returncode, self.stdout, self.stderr
        )


def test_codex_worker_builds_json_command_and_parses_implementation():
    runner = MockRunner(
        stdout='{"type":"item.completed","item":{"type":"agent_message",'
        '"text":"{\\"output\\":{\\"revision\\":2},\\"summary\\":\\"done\\"}"}}\n'
    )
    adapter = CodexAdapter(cwd=".", runner=runner)

    output = adapter.run(
        RoleSpec("worker", "codex", {"model": "gpt-5.6-luna", "effort": "high"}),
        "build task",
        {"phase": "implementation", "round": 1},
    )

    command, kwargs = runner.calls[0]
    assert command[:3] == ["codex", "exec", "--ephemeral"]
    assert "--json" in command
    assert "workspace-write" in command
    assert "gpt-5.6-luna" in command
    assert 'model_reasoning_effort="high"' in command
    assert '"phase": "implementation"' in kwargs["input_text"]
    assert output == {"revision": 2}


def test_claude_reviewer_uses_plan_and_parses_structured_verdict():
    runner = MockRunner(
        stdout=(
            '{"type":"result","structured_output":{"status":"APPROVED",'
            '"summary":"looks good","findings":[]}}'
        )
    )
    adapter = ClaudeAdapter(cwd=".", runner=runner)

    verdict = adapter.run(
        RoleSpec(
            "reviewer",
            "claude",
            {"model": "opus", "effort": "low", "api_key": "do-not-send"},
        ),
        "review task",
        {"phase": "audit", "round": 1, "worker_output": {"ok": True}},
    )

    command, kwargs = runner.calls[0]
    assert "--output-format" in command
    assert "json" in command
    assert ["--permission-mode", "plan"] == command[
        command.index("--permission-mode") : command.index("--permission-mode") + 2
    ]
    assert "Read,Grep,Glob" in command
    assert "do-not-send" not in kwargs["input_text"]
    assert verdict.status is VerdictStatus.APPROVED
    assert verdict.summary == "looks good"


def test_opencode_finding_response_uses_plan_only_for_reviewers_and_parses_json_event():
    runner = MockRunner(
        stdout=(
            '{"type":"text","part":{"text":"{\\"responses\\":['
            '{\\"finding_id\\":\\"F1\\",\\"disposition\\":\\"ACCEPT\\",'
            '\\"rationale\\":\\"fixed\\"}]}"}}\n'
        )
    )
    adapter = OpenCodeAdapter(cwd=".", runner=runner)

    response = adapter.run(
        RoleSpec("worker", "opencode", {"model": "local/model", "effort": "high"}),
        "respond task",
        {"phase": "finding_response", "round": 1},
    )

    command, kwargs = runner.calls[0]
    assert command[:4] == ["opencode", "run", "--format", "json"]
    assert "--agent" in command and command[command.index("--agent") + 1] == "build"
    assert "--variant" in command and "high" in command
    assert kwargs["input_text"] is None
    assert isinstance(response, WorkerResponse)
    assert response.responses[0].disposition is FindingDisposition.ACCEPT


@pytest.mark.parametrize(
    ("adapter_cls", "phase", "required"),
    [
        (CodexAdapter, "audit", "read-only"),
        (ClaudeAdapter, "consensus", "plan"),
        (OpenCodeAdapter, "audit", "plan"),
    ],
)
def test_reviewer_routes_have_read_only_controls(adapter_cls, phase, required):
    runner = MockRunner(stdout='{"status":"APPROVED","summary":"ok","findings":[]}')
    adapter = adapter_cls(cwd=".", runner=runner)
    adapter.run(RoleSpec("reviewer", "backend", {}), "task", {"phase": phase})
    command, _ = runner.calls[0]
    assert required in command


def test_quota_errors_are_classified_as_adapter_failure():
    runner = MockRunner(stderr="HTTP 429: rate limit exceeded", returncode=1)
    adapter = CodexAdapter(runner=runner)

    with pytest.raises(AdapterFailure) as error:
        adapter.run(RoleSpec("worker", "codex"), "task", {"phase": "implementation"})

    assert error.value.kind is AdapterFailureKind.QUOTA


def test_success_exit_with_provider_error_event_is_still_classified():
    runner = MockRunner(
        stdout='{"type":"error","error":{"message":"provider overloaded"}}'
    )
    adapter = OpenCodeAdapter(runner=runner)

    with pytest.raises(AdapterFailure) as error:
        adapter.run(RoleSpec("reviewer", "opencode"), "task", {"phase": "audit"})

    assert error.value.kind is AdapterFailureKind.PROVIDER


def test_shared_runner_resolves_direct_executable_from_windows_cmd_shim(
    monkeypatch, tmp_path
):
    target = tmp_path / "node_modules" / "opencode-ai" / "bin" / "opencode.exe"
    target.parent.mkdir(parents=True)
    target.touch()
    shim = tmp_path / "opencode.cmd"
    shim.write_text(
        '@ECHO off\n"%dp0%\\node_modules\\opencode-ai\\bin\\opencode.exe" %*\n',
        encoding="utf-8",
    )
    calls = []

    monkeypatch.setattr(adapter_module.shutil, "which", lambda _: str(shim))

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "1.0.0", "")

    monkeypatch.setattr(adapter_module.subprocess, "run", fake_run)

    result = adapter_module.run_subprocess(["opencode", "--version"])

    assert result.returncode == 0
    assert calls[0][0] == [str(target.resolve()), "--version"]
    assert calls[0][1]["shell"] is False


def test_cli_defaults_match_real_role_backends_and_demo_remains_available():
    args = build_parser().parse_args(["task"])
    roles = roles_from_args(args)

    assert roles.worker.backend == "codex"
    assert roles.worker.options == {"model": "gpt-5.6-luna", "effort": "high"}
    assert roles.reviewer.backend == "claude"
    assert roles.reviewer.options == {"model": "opus", "effort": "low"}
    assert roles.fallback_reviewer.backend == "opencode"

    override_args = build_parser().parse_args(["task", "--backend", "opencode"])
    override_roles = roles_from_args(override_args)
    assert override_roles.worker.backend == "opencode"
    assert "model" not in override_roles.worker.options
    assert override_roles.reviewer.backend == "opencode"
    assert "model" not in override_roles.reviewer.options

    demo_args = build_parser().parse_args(["task", "--demo"])
    demo_roles = configured_roles_from_args(demo_args)
    assert demo_roles.worker.backend == "default"
    assert demo_roles.reviewer.backend == "default"

def test_safe_role_options_redacts_composite_credential_keys():
    options = {
        "client_secret": "do-not-send",
        "private_key": "also-do-not-send",
        "credential_id": "still-do-not-send",
        "model": "gpt-5.6-luna",
    }

    safe = adapter_module._safe_role_options(options)

    assert safe == {"model": "gpt-5.6-luna"}
