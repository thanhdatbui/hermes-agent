# Approved-plan implementation gate (Windows / MSYS)

Session-derived reference for the transition from an independently approved plan to a delegated implementation worker.

## 1. Bind the approval

Record, before dispatch:

- exact plan path, SHA-256, byte count, line count, and EOL/BOM facts;
- independent reviewer artifact and parseable first-line verdict;
- consumer/core baseline HEADs;
- exact implementation allowlist;
- worker worktree paths and branches.

Any later plan, source, test, rule, HANDOFF, or compatibility-record edit invalidates the approval and requires a fresh binding/audit.

## 2. Create Windows worktrees safely

The terminal is MSYS/bash, but Git on Windows resolves native paths differently. Use this pattern:

```bash
cd '/d/Taadaa/<source-repo>'
git worktree add -b 'codex/<branch>' 'D:/Taadaa/<target-worktree>' '<exact-baseline-sha>'
```

Do **not** use `git -C /d/...` when the `-C` value refers to another native target. A mixed `/d/...` + native-path command can silently create `D:\\d\\Taadaa\\...` while returning success.

After every create, verify from the target itself:

```bash
git -C 'D:/Taadaa/<target-worktree>' rev-parse --show-toplevel
git -C 'D:/Taadaa/<target-worktree>' branch --show-current
git -C 'D:/Taadaa/<target-worktree>' rev-parse HEAD
git -C 'D:/Taadaa/<target-worktree>' status --short --untracked-files=all
```

### Partial creation recovery

If a multi-repo creation command fails after creating one worktree:

1. stop; do not retry the whole command;
2. inspect `git worktree list --porcelain` in each repository;
3. identify only the wrong path and newly created temporary branch;
4. remove that exact worktree and branch;
5. verify the target path is absent and the original worktree is unchanged;
6. create each remaining worktree separately and verify it.

Never use blanket cleanup or reset/clean on a dirty coordinator checkout.

## 3. Classify active processes

A process gate must inspect command lines and distinguish:

- recovery-specific launchers/watchers/supervisors: these must be idle;
- unrelated automation, such as a proxy-only tray: record it as unrelated and leave it running.

Do not kill or restart an unrelated process merely to satisfy an “idle” label. Report both `recovery-specific=IDLE` and the unrelated-process disposition.

## 4. Worker handoff

The worker brief should include:

- exact absolute worktrees, branches, and baseline SHAs;
- “before every command, enter the source repo, then explicitly enter the intended native target” when the environment has a path trap;
- strict TDD RED → GREEN order;
- no commit/push/deploy/live action unless separately authorized;
- explicit allowlist; preserve coordinator dirty hunks, and do not touch only hunks with proven overlap or active ownership;
- requirement to return absolute paths, changed files, real RED/GREEN commands and results, and compatibility disposition.

## 5. Parent verification after completion

Do not verify while the worker is still writing. On completion, independently run:

1. process state and worker-handle reconciliation;
2. exact target `HEAD`/branch/status and untracked-file inventory;
3. allowlist check including files omitted by `git diff --name-only`;
4. per-file hash/size/EOL/BOM and scoped diff review;
5. fresh RED attribution where required, then targeted GREEN and final canonical suites;
6. external-temp `py_compile`, AST/test inventory, `git diff --check`, and adversarial fail-closed probes;
7. a new exact-byte implementation audit before any commit/push.

A worker exit status, notification, hash it reports, or test count it quotes is never sufficient by itself.

## 6. Tool-budget discipline

Avoid repeated status polls and repeated “still running” messages. Use bounded polling with a meaningful interval and combine independent read-only checks. If the session/tool budget ends while the worker is active, preserve the checkpoint and report `IN_PROGRESS` or `BLOCKED`; do not convert an unfinished worker into `GREEN`, `VERIFIED`, or `DONE`.
