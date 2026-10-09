---
name: focused-test-repair
description: "Use when focused tests are malformed. Repair and verify."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [pytest, test-repair, structural-repair, payloads, verification]
    related_skills: [systematic-debugging, agent-verification-loop, verification-evidence]
---

# Focused Test Repair and Verification

## Purpose

Repair narrowly scoped Python production/test changes without broad refactors,
then prove the final live bytes with the user's exact verification commands. This
skill is for malformed focused tests, duplicate test definitions, orphaned test
bodies, and contract changes where an old size-limit rejection must become a
large-payload send-through regression.

## Workflow

1. **Bind scope before editing.** Record the exact repository root, target files,
   required command lines, and the no-commit/no-push boundary. Inspect status and
   the live target files. Preserve unrelated dirty and untracked paths.
2. **Find the structural root cause.** Parse or compile the test file before
   behavioral interpretation. Locate duplicate definitions, missing `def`
   boundaries, orphaned bodies, and stale assertions referring to removed
   production constants. Read complete target context before patching; partial or
   truncated reads are not safe patch anchors.
3. **Make the smallest repair.** Keep one canonical test for each contract.
   Restore a missing function declaration around the existing body. Replace only
   the stale test required by the new contract; do not rewrite neighboring tests.
4. **For unlimited/full-context routes, separate guards.** Keep the exact-model
   authorization restriction and UTF-8 serialization. Remove artificial payload
   ceilings only from the explicitly authorized full-context route; leave the
   ordinary guarded route fail-closed. Provider/HTTP failures must remain
   fail-safe rather than becoming approval.
5. **Test acceptance/send-through behavior.** Mock the response and transport,
   construct one payload materially above the former threshold, and assert all of:
   exact authorized model, no truncation/rejection, a distinctive full tail (or
   complete diff) in posted bytes, and that the transport was called.
6. **Preserve precedence rules.** A valid rubric at or above threshold overrides
   advisory `ready_to_close` values, including `false` and the string `"false"`.
   An explicit `NEED_CONTEXT` marker remains fail-closed and takes precedence.
7. **Verify only after the last edit.** Run the exact focused pytest command,
   then the requested compile/static checks and diff check. Any test-file edit
   invalidates earlier results. If the execution budget expires, report every
   missing anchor and every unrun command explicitly; never summarize a partial
   patch as complete.
   If a prior worker already changed the regression test, first run that exact
   node to establish RED against the live production bytes, preserve the test
   when it matches the requested contract, and patch only the production seam.
   After the source edit, rerun the exact node; a broader focused module run may
   expose unrelated pre-existing failures, which must be reported separately
   rather than repaired opportunistically or used to invalidate the targeted
   regression result.
8. **Exercise safety gates through the real wrapper path.** When a fail-closed
   cooldown, lock, ownership, or authorization gate is involved, mock the gate
   seam and invoke the public/full execution path—not only the helper. Assert the
   exact skip/failure payload, zero forbidden side effects, and that corrupt or
   invalid state is represented by the fail-closed result. If a broad catch can
   convert a gate error into continued work, narrow/remove only that local catch
   and add an observability regression before touching neighboring behavior.

## Repository-root and Git-diff diagnostics

Bind the repository location before any file search or test command. Treat a
user-supplied Windows path as authoritative: validate that the exact path exists
and run `git -C <exact-path> rev-parse --show-toplevel` before trying alternate
drive mappings, parent directories, or similarly named checkouts. Do not infer
`/d/...` or `/D/...` translations from a native `D:\\...` path; MSYS mounts and
nested worktrees can differ. If the exact path is unavailable or is not the
requested repository, stop with a concrete path/root blocker rather than
searching broad user/drive roots or editing a lookalike checkout.

On Windows farm repositories, the user-facing project directory may not be the
Git root. Before scoped Git commands, resolve the root with
`git -C <candidate> rev-parse --show-toplevel`, then run status/diff checks from
that returned directory (or keep using `git -C`). An absolute pytest path may
still collect successfully from a parent directory, so a passing test does not
prove the chosen working directory is the repository root.

When the task supplies an exact workspace path and authorized filenames, bind
those inputs before any write or test: inspect the supplied path directly, check
only bounded known subdirectories/candidates, and verify both target files exist
in the same repository. Do not launch an unbounded recursive scan from a
protected user/drive root; it is noisy, can trigger safety guards, and does not
establish repository ownership. If the files or Git root cannot be found, stop
with a concrete blocker and do not patch or claim verification.

If `git diff` fails with `cannot spawn : No such file or directory` / `external
diff died`, treat it as Git configuration/tooling interference rather than a
code failure. Re-run the scoped diff with the configured external diff disabled
(for example `git -c diff.external= -C <repo> diff -- <allowlist>`), then retain
the required `git diff --check` scope. Keep the exact user verification command
unchanged when it is part of the acceptance contract; use the override only to
obtain diagnostic diff evidence.

See `references/structural-repair-and-full-context.md` for the compact repair
checklist and assertion pattern. See
`references/windows-nested-root-and-diff.md` for the nested-root/external-diff
recipe. For offline Git candidate extraction/binding parity and oversized
working-tree cases, use `references/offline-git-candidate-binding.md`.

## Offline Git candidate binding coverage

When the closeout code supports both staged and non-targeted working-tree
candidates, add real `tmp_path` repositories rather than only mocking Git
helpers. Start from a committed tracked file, make an unstaged edit, run the
actual extractor, then resolve the actual binding and compare the canonical
SHA-256 bytes. The test must assert the working-tree mode and exact scope.
For oversized candidates, force a small extraction limit and assert the
truncation marker plus the extracted hash; compare it with the raw working-tree
binding hash and prove the mismatch is rejected before reviewer transport. This
prevents a truncated representation from being accepted as the full candidate.
All subprocess Git reads used by production and tests should be hermetic
(`--no-ext-diff`, disabled fsmonitor/hooks where applicable); ambient external
diff configuration can otherwise turn a valid local Git fixture into a false
empty/error result.

## Bounded single-file pipeline repairs

For a task with an explicit call/iteration budget and a named production file:
1. **Bind the schema and anchors early.** Inspect the live source and canonical
   input fixture before editing; confirm the exact function boundaries and output
   contract within the first few calls.
2. **Prefer uniquely anchored patches.** Use small targeted edits rather than
   generated shell/Python rewrites. Multiline scripts nested inside shell or
   Python string literals are prone to quote collisions and can fail before
   touching the target, obscuring whether the product changed.
3. **Verify after the final edit.** Run the exact compile check, then execute the
   requested pipeline with the real fixture and inspect its actual status and
   generated artifacts. Any earlier output is stale after a later edit.
4. **Spend the last calls on acceptance evidence.** If the budget is nearly
   exhausted, prioritize final compile and pipeline execution over cosmetic
   inspection; report `BLOCKED` rather than claiming `READY` when final
   execution was not completed.
5. **Keep status fail-closed.** Validation failure must preserve the draft/review
   state. A ready status requires fresh evidence from the final bytes and outputs.

## Remote-dispatch seams in bounded production fixes

When a controller must dispatch work to a remote host, branch before any local filesystem probe that belongs to the remote host. Preserve the local branch's existing validation and command byte-for-byte where required; make the remote branch explicit with the exact alias, remote working directory, runtime, module, config, workbook slot, serial, item number, source root, and safety flags. Build the remote command so the remote shell performs its own `cd`, and explicitly remove controller-only environment variables (for example `ADB_SERVER_SOCKET`) from the environment passed to the SSH subprocess. Reuse the existing stdout/report/ledger verification path rather than adding a parallel success heuristic; retain fail-closed behavior for missing or invalid markers. Mock the subprocess and assert both branches, including that the remote branch never calls local `is_file()`/`stat()` on remote media.

## UI recovery actions require verified postconditions

For bounded UI/device recovery fixes, treat a tap, relaunch, swipe, or force-stop
as an **action**, never as proof of recovery. The recovery seam must:

1. Select the intended control from authoritative UI evidence using the narrowest
   stable identity available (resource-id first, then exact text/content-desc,
   with bounds recorded for auditability). Do not fall back to blind center-screen
   taps when the expected control is absent.
2. Capture a fresh UI/XML observation after the action. The post-capture must be
   newer than the action and must be fed through the same detector used by the
   caller.
3. Publish success only when the network/error marker is absent and the expected
   terminal screen is present. If the marker remains, return an explicit
   fail-closed result with the latest artifact path, attempt count, and reason.
4. If a bounded relaunch/retry is part of the contract, apply a small explicit
   budget and verify after every retry. Never convert a successful tap or command
   return code into `recovered` without the postcondition.
5. Add offline mocked regressions for both branches: marker remains after the
   action (must not succeed) and marker disappears after the fresh capture (may
   succeed). Keep device/network operations mocked.

For selector-based Android recovery, inspect the real XML shape before writing
fixtures: a button can be a wide row whose actionable bounds differ from the
nearest text node. Assert the selected resource-id/text/bounds and the ordered
observation calls, not merely that a tap method was invoked. The compact
network-retry fixture and acceptance matrix are in
`references/ui-recovery-postcondition-contract.md`.

## Safe script-based edits on Windows

When applying a user-supplied multiline patch through `python -c`, treat the
edit as a transaction rather than mutating the target in place:

1. Read each target fully into memory before opening any output handle.
2. Apply and assert every exact replacement in memory; an assertion failure must
   leave the target untouched.
3. Write to a same-directory temporary file, preserve the target's original EOL
   style, flush/close it, then replace the target only after the complete
   transform succeeds. Never use a list comprehension or chained expression
   that opens the destination with `wb`/`w` before opening the source with `rb`/`r`;
   evaluation order can truncate the source before it is read.
4. After every write, immediately check byte size, `py_compile`, and the exact
   focused test. If a file unexpectedly becomes empty or its line count drops,
   stop all further edits and recover from a saved preimage in an isolated
   worktree/temp clone—not from memory and not with a broad restore in a shared
   worktree.
5. Prefer a small external script/temp file over deeply nested shell/Python
   quoting for multiline test literals. Escaped `\\n` intended for source code
   must be verified as literal backslash-plus-`n`, not accidentally materialized
   as a newline inside a quoted Python string.

See `references/windows-script-patch-safety.md` for the failure pattern and a
transactional replacement recipe.

## Pitfalls

- Preserve the target file's existing line-ending convention when applying targeted patches. Mixed CRLF/LF hunks can make `git diff --check` report false-looking trailing-whitespace errors across otherwise unchanged lines; inspect `file`/byte counts and normalize only the edited targets transactionally if needed. After any line-ending normalization, rerun the exact focused pytest, compile, and diff-check commands because all earlier evidence is stale.
- For bounded closeout work, bind the Git root and exact allowlist before
  editing, inspect only the named anchors, and fail fast if the requested
  evidence/patch cannot fit the call budget. Do not spend the final calls on
  broad discovery; reserve them for the exact pytest, diff-check, and numstat
  evidence.
- When adding a regression test, preserve the file's existing import bootstrap
  and module namespace conventions. Inspect how neighboring tests put local
  packages on `sys.path` and import the production module before introducing a
  new package-qualified import. Run collection with the canonical repository
  command after the final test edit; a collection/import error is harness
  setup evidence, not a production pass or a reason to patch production
  speculatively.
- Avoid broad or generic replacement anchors such as a lone `try:`, `except:`,
  closing brace, or repeated dictionary fragment. A replacement that matches the
  wrong occurrence can silently delete a required statement while leaving a
  superficially plausible file. Use a unique function-local block and run
  `py_compile` immediately after each production edit.
- Do not merely assert that a large request does not raise. Inspect the posted
  UTF-8 JSON and assert the exact model plus a unique tail from the full diff.
- Do not remove the exact-model restriction while removing a size ceiling.
- Do not use a former payload-limit constant in tests after removing it from
  production.
- Do not trust pre-edit pytest output after changing the focused test file.
- Do not touch unrelated dirty/untracked files, commit, or push when the task
  explicitly forbids those actions.
- Keep path and repository-root failures separate from code failures: a command
  run from the wrong directory must be rerun from the resolved Git root before
  reporting verification as failed. For diagnostic diff display, prefer the
  `git -c diff.external= ... diff` workaround; do not replace the mandated
  `git diff --check` gate with an ad-hoc command.
- When adding hermetic tests for fallback/default contracts (telemetry, fallback IDs, unset-env branches), verify whether shared test runner helpers seed or inherit ambient environment variables (such as `env.setdefault(...)`). Explicitly clear those variables (for example, with `monkeypatch.delenv(..., raising=False)`) in the test body so ambient or fixture-provided values do not flip `is_fallback` assertions or mask default behavior.

## Verification

For a Windows Git Bash repository, run commands from the actual repository root
and quote paths containing spaces. Use the exact user-provided runner rather than
substituting a broader suite. Report real exit codes and counts separately from
any ad-hoc probe.
