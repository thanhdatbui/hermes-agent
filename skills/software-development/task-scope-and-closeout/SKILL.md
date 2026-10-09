---
name: task-scope-and-closeout
description: "Use before mixed-session closeout to bind scope."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [scope, closeout, runtime-config, git, evidence, orchestration]
    related_skills: [session-close-protocol, closeout-review-discipline, scope-lock, ui-evidence-first]
---

# Task Scope and Closeout

Use this class skill when a session mixes app configuration, skill/rule edits, repository work, screenshots, or a user command such as `chốt phiên`, `done`, or `wrap up`.

## 1. Classify before acting

### Anti-Premature `/new` & Session Continuity Invariant

When receiving a continuation prompt (e.g. user attaches a screenshot of an interrupted chat, says "Ủa k làm nốt ở session này đc à", or "Xử lý tiếp session này cho t"):
- Never prematurely advise `/new` or claim the work must wait for a fresh session when the current session is healthy and capable of executing.
- Use `session_search` to recover the previous turn's exact context, unresolved requests, and uncommitted diffs.
- Formulate an immediate O(1) Patch Contract or focused worker dispatch to drive the remaining task to completion without forcing unnecessary session churn.

Create a short scope record before any closeout command:

### Mandatory decomposition gate

Before dispatching or editing a code candidate, split the user's request by semantic concern and lifecycle. Never bundle unrelated production fixes, tests, docs cleanup, UI recovery, and batch jobs merely because they share a repo or farm session. For each subtask record one component, exact source/test allowlist, acceptance command, and whether it needs its own verification/closeout receipt. A practical default is one component and at most two code/test files per worker dispatch; mandatory repository catalog/docs are a separate documentation lane and must not silently expand a code-surgery contract. If a finding is discovered outside the user's requested scope, report it but do not turn it into follow-up work without a new scope decision.

Treat a closeout rejection as evidence about the exact bound candidate, not permission to widen the candidate. First restore scope by reverting or excluding unrelated behavioral hunks through the authorized worker, then remediate the remaining finding in a smaller contract. Do not grow a six-file diff by adding tests for every reviewer suggestion when the suggestion concerns an unrelated baseline regression; either isolate that concern as a separate task or explicitly classify it as out of scope with evidence.

Create a short scope record before any closeout command:

- `CODE_CANDIDATE`: a known repository, exact source/test files, and a code deliverable were changed in this session.
- `DOC_POLICY`: tracked documentation, skill, or rule files changed; no production-code deliverable was requested.
- `RUNTIME_CONFIG`: an application or user-local setting changed and was verified in the running app. Runtime state is not automatically Git-backed.
- `NO_CANDIDATE`: no current-session artifact can be bound to a repository and allowlist.

Never infer ownership from whatever repositories happen to be dirty. Dirty files from earlier sessions or other workers are foreign until current-session evidence binds them.

## 2. Closeout routing

- Only `CODE_CANDIDATE` authorizes `closeout_gate.py`; bind the canonical repo, actual base semantics, and exact `--files` list first.
- `DOC_POLICY` may receive a focused policy/document review only when publication or commit is explicitly part of the request. Do not sweep unrelated repositories.
- `RUNTIME_CONFIG` is closed by direct application readback and a concise runtime receipt; do not claim a Git commit is needed for a Claude Desktop model/advisor selection.
- `NO_CANDIDATE` is `NOT_APPLICABLE — no code candidate`, not a reason to guess `HEAD~1`, enumerate all dirty repositories, or run a reviewer against an arbitrary repo.

A closeout receipt should contain only: `session_class`, `repo` (if any), `base` (if any), `files`, `gate_status`, `commit_required`, and `evidence_paths`.

## 3. Persistence ledger

Keep two ledgers separate:

1. **Runtime ledger:** settings stored by the running app/profile. Verify through the app or its authoritative runtime readback.
2. **Declarative ledger:** tracked Hermes skills/rules/config templates. These belong in the canonical tracked repository and need explicit publication/commit scope.

Do not confuse “saved in the app” with “saved in Git,” and do not confuse “dirty in Git” with “part of this session.”

## 4. External CLI and budget discipline

Call an external CLI only when the user explicitly requests it or the active task contract names it. For `claude -p`, omit `--max-turns` for bounded tasks when the terminal timeout is the safety bound, or derive a sufficient budget: simple read-only `10`, standard implementation/review `15`, complex multi-file `20+` only with justification. A `Reached max turns` / `error_max_turns` result is `CALLER_BUDGET_INSUFFICIENT`, not a product or repository failure; rerun with narrowed scope or sufficient budget, never the same tiny cap.

## 5. Evidence and reporting

For UI or screenshot deliverables, inspect the exact artifact before claiming it proves anything: verify path/existence/freshness, read the pixels or OCR/vision content, confirm the target app/window and semantic result, then send `MEDIA:`. If the image is the wrong foreground app, stale, blank, or unrelated, reject it and capture a new artifact. Report one direct verdict first, followed by only the evidence needed to support it.

## References

See `references/runtime-vs-git-and-closeout.md` for the compact decision table, bounded receipt template, and the incident pattern that motivated this skill.

## Overlap note

This skill complements rather than replaces `session-close-protocol` and `closeout-review-discipline`: those skills define the reviewer/remediation mechanics; this skill decides whether those mechanics apply to the current session at all.
