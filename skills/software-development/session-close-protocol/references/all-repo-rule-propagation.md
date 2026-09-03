# All-repo rule propagation

Use this reference when a user asks to update a rule, hard trigger, policy, or skill guard across **all repositories**. Do not treat the two repos mentioned in the incident as the whole workspace.

## 1. Build the real active-repo inventory

- Start from the workspace root, normally `D:\Taadaa`.
- Enumerate candidate top-level project directories and verify each independently with `git -C <dir> rev-parse --show-toplevel`.
- Do not infer the inventory from a recursive `.git` walk: a parent `.git` directory can make unrelated directories look like one checkout, and backup/worktree trees can create false targets.
- Exclude backup, runtime, build, release, artifact, cache, `node_modules`, generated, and temporary trees unless the user explicitly names them.
- Record the exact active checkout list before editing.

## 2. Define the rule-file allowlist

For each active checkout, inspect tracked context/policy files with:

```text
git -C <repo> ls-files -- '*AGENTS.md' '*CLAUDE.md' '*PROJECT_RULES.md' '*.hermes.md' '*HERMES.md' '.cursorrules' '.cursor/rules/*.mdc'
```

Then add explicitly discovered nested policy files that are loaded by a sub-application (for example `Hermes\apps\desktop\AGENTS.md`) and workspace-wide policy files outside a checkout (for example `D:\Taadaa\AGENTS.md` and `D:\Taadaa\HERMES_SUBAGENT_RULES.md`). Distinguish local policy adapters from non-policy templates: a file such as `skills\...\templates\claude.md` is a design/template asset and must not receive orchestration rules. Do not silently omit a common orchestration rule merely because it is not inside a repo.

The allowlist must contain absolute paths and a reason for inclusion/exclusion. Never claim “all repo” from an allowlist containing only the two repos in the incident.

## 3. Capture a pre-write baseline

For every allowlisted file, record:

- absolute path;
- tracked/untracked state and repo branch/status;
- byte count and SHA-256;
- CRLF, lone-LF, lone-CR, and line counts;
- whether the target marker already exists;
- a recoverable backup under a timestamped temp evidence directory.

Do not stage or modify secrets, credentials, workbooks, device state, runtime output, or foreign-worker artifacts.

## 4. Propagate without normalization churn

- Use one canonical rule block as the source; append only when the marker is absent.
- Preserve the existing file bytes and newline style. Do not rewrite the entire file through a text-mode conversion.
- Refuse duplicate markers and abort on a missing target.
- Keep the operation idempotent: a second run must report `ALREADY_PRESENT`, not append a second block.
- Do not commit or push merely because propagation succeeded; that is a separate user-authorized closeout action.

## 5. Verify independently

For every target, verify:

- marker count is exactly one;
- all required phrases are present, including the action trigger, `BLOCKED_AT_<STEP>`, `fetch/pull --rebase`, and remote-SHA verification;
- the old bytes are an exact prefix of the new bytes when the operation is append-only;
- EOL counts changed only by the appended block;
- a rerun is idempotent.

Run repository-scoped diff checks. For CRLF repositories, the correct Git option placement is:

```text
git -c core.whitespace=cr-at-eol diff --check
```

A raw `git diff --check` may report pre-existing CRLF bytes as trailing whitespace. Distinguish that warning from actual content churn by comparing the baseline bytes and using `git diff --ignore-space-at-eol`; do not “fix” line endings globally just to silence the warning.

## 6. Commit and report honestly

If the user explicitly triggers closeout after propagation, commit each repository's exact policy candidate separately. Resolve each repository's configured upstream from Git rather than assuming `origin/<current-branch>`. Preserve unrelated dirty/staged work; when a file has pre-existing staged content, build the commit from a temporary index containing `HEAD` plus only the approved rule suffix. If normal commit hits a stale temporary-index lock, prove no active writer owns it and use a fresh isolated index instead of deleting locks blindly.

Verify each pushed policy commit by exact subject/path scope and by ancestry on both local and remote refs. A later concurrent commit may move `HEAD` beyond the policy commit, so checking only whether `HEAD` itself is the docs commit is incorrect. Report the active-repo count, allowlisted-file count, appended/already-present counts, verification result, evidence directory, and any excluded or unresolved paths. State explicitly whether the changes are local only or were committed/pushed. “All repo updated” is valid only after the inventory, marker verification, commit scope, and remote ancestry cover the complete allowlist.
