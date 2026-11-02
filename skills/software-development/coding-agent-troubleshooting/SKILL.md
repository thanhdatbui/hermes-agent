---
name: coding-agent-troubleshooting
description: "Diagnose and fix common CLI failures for Codex and Claude Code — sandbox, PATH, auth, version conflicts."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [troubleshooting, codex, claude, sandbox, windows, debugging]
    related_skills: [codex, claude-code, hermes-orchestration-dispatcher]
---
# Coding Agent Troubleshooting

Quick-reference diagnostic patterns for Codex CLI and Claude Code failures.
Load this skill when any coding agent returns infrastructure errors (sandbox, PATH, auth, shell).

## First Step for Any Agent

```
<agent> doctor    # Always the first diagnostic command
<agent> --version # Confirm running version
```

## Codex CLI — Windows Process-Boundary Failures

For the verified OmniRoute pool-routing, Windows sandbox workaround, background confirmation hang, and obsolete `.codex/agents/*.toml` field cleanup procedure, see `references/codex-cli-omniroute-routing-and-confirmation-hang.md`. Always distinguish a provider/quota failure from a CLI routing failure by checking the effective `provider:` line in Codex output; do not report pool exhaustion until an OmniRoute-routed smoke request has failed.

### UTF-8 stdin on Windows

When an invoked CLI rejects a non-ASCII prompt with an error such as `input is not valid UTF-8`, treat it as a subprocess boundary bug before treating it as a provider/model failure. Python `subprocess.run(..., text=True, input=...)` should pass `encoding="utf-8"` explicitly when the child protocol is UTF-8; do not rely on the Windows locale code page. Add a regression fixture containing Vietnamese or another non-ASCII string, and assert the capture seam receives the explicit encoding.

### Structured output routing

Capture stdout, stderr, exit code, and any provider result file independently. Normalize only documented/equivalent envelopes at the consumer boundary (for example fenced/prose JSON, `result`/`content` wrappers, or an advisor `status` plus plan fields), then validate the role-specific canonical schema. Keep advisor plans separate from executor patch decisions: a ready advisor response must not be mistaken for permission to run live, and an incomplete executor response must fail closed rather than being retried as an unstructured success.

See `references/utf8-and-structured-output-boundaries.md` for the reusable reproduction and verification matrix.

### Diagnostic Commands

```bash
<agent> doctor
<agent> --version
```

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
