# Two-Agent Review Loop Prompts

Used when modifying Hermes code itself (deploy, skills, core). Codex plans and codes; Claude audits.

## Codex — Plan (plan only, no edits)

```
Create an implementation plan only; do not edit files or commit. Scope: <describe>.
Inspect <paths/files>. Return a concrete plan with exact files, migration steps,
Windows behavior, tests, and acceptance criteria. Account for dirty unrelated
working tree and do not touch it.
```

## Codex — Code (implement the plan)

```
Implement the approved plan. You may edit ONLY: <file list>. Do not touch any
other existing dirty files. Requirements: <list>. Run focused tests, PowerShell
parse, and git diff --check. Do not commit or push; return changed files, test
outputs, and note any blockers.
```

## Claude — Audit (verify, no edits)

```
Audit the current implementation. Do not edit files or commit. Review ONLY:
<file list>. Check correctness against requirements: <list>. Identify any
blocking bugs with exact file/line references. Return PASS/FAIL and concise
fixes.
```

## Key constraints to enforce in prompts

- "Do not touch any other existing dirty files" — prevents unrelated working-tree churn
- "Do not commit or push" — keeps the human in control of the commit
- "Do not modify unrelated dirty files" — repeat for both agents
- "Account for dirty unrelated working tree" — for the planner
- Specify exact file list the agent MAY edit — scope containment

## Pitfall: Codex sandbox failures on Windows

If Codex errors with `orchestrator_helper_launch_failed` or `codex-windows-sandbox-setup.exe not found`, add `--sandbox danger-full-access` to the Codex command. This is a known Windows sandbox bootstrap issue, not a code problem.

## Pitfall: Codex max-turns exhausted

If Codex hits max turns mid-task, it returns `Error: Reached max turns (N)`. Increase `--max-turns` to 15-20 for complex reviews. Codex may still produce useful output in the transcript even if exit code is 1.

## Pitfall: Claude returns empty result

Claude with `claude -p` may return `Error: Reached max turns (8)` with no output if the task requires too many tool calls. Use `--max-turns 15-20` for audit tasks that need to read multiple files.
