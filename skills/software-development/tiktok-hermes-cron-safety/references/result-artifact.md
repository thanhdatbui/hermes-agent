# Worker result artifact for Phase 9A.x safety changes

Write the handoff **outside the repository**, for example:

`C:\Users\Kibe\AppData\Local\hermes\cache\terminal\phase9-<task>-<attempt>-worker-result.json`

The artifact is a worker handoff, not approval. The coordinator must independently verify its claims against the exact worktree.

## Required shape

```json
{
  "task": "<phase/task>",
  "attempt": "<implementation or remediation attempt>",
  "started_utc": "<ISO-8601>",
  "ended_utc": "<ISO-8601>",
  "profile": "<actual worker profile if observable>",
  "model": "<actual model if observable>",
  "worktree": "<absolute authority-worktree path>",
  "baseline": {
    "branch": "<expected branch>",
    "head": "<baseline SHA>",
    "clean_or_expected_scope": true
  },
  "method": "strict TDD; NO-LIVE; no commit",
  "write_allowlist": ["<repo-relative path>"],
  "changed_files": [
    {"path": "<repo-relative path>", "sha256": "<final hash>", "bytes": 0}
  ],
  "red": {
    "command": "<exact command>",
    "exit_code": 1,
    "reason_confirmed": "<why this was the expected missing-feature failure>"
  },
  "green": [
    {"command": "<exact focused command>", "exit_code": 0, "summary": "<count>"},
    {"command": "<exact full-suite command>", "exit_code": 0, "summary": "<count>"}
  ],
  "static_gates": {
    "py_compile": "PASS",
    "git_diff_check": "PASS",
    "allowlist": "PASS",
    "lf_crlf_bom": "PASS",
    "ast_no_removed_or_nested_tests": "PASS"
  },
  "no_live": {
    "adb_or_device_access": false,
    "live_subprocess": false,
    "workbook_or_credentials_read": false
  },
  "git_status_short": "<exact final status>",
  "blockers": [],
  "result": "PASS"
}
```

## Truthfulness rules

- Write `PASS` only after the focused tests, full required suite, and every static gate pass on the final bytes.
- If any failure remains, use `result: "BLOCKED"`, preserve the failing command/output summary, and name the concrete next step. Never report a partial green slice as completion.
- Do not fabricate an artifact after a worker disappears. A missing artifact means the coordinator must inspect process/writer state and verify the worktree directly.
- A worker artifact does not authorize commit. Exact-byte auditor `APPROVED` plus coordinator hash/status verification is still required.
- If source/test files changed after `ended_utc`, invalidate the artifact and regenerate it.
- Never include credentials, workbook row contents, account data, or unredacted secrets.
