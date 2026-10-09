---
name: policy-documentation-hardening
description: "Use for exact-allowlist policy documentation hardening."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [policy, documentation, allowlist, precedence, eol, verification]
    category: software-development
---

# Policy Documentation Hardening

Use this class skill when a user requests a narrowly scoped change to orchestration rules, workspace policy, or skill documentation across an explicit allowlist, especially when the user forbids candidate-code changes and commit/push.

## Contract

Before editing, record:

- canonical source file and exact insertion/replacement anchor;
- pointer/adaptor files and the one-way precedence relationship;
- exact allowlist and explicit non-goals;
- marker/heading occurrence requirements;
- EOL/BOM/byte-preservation requirement;
- final verification commands and the no-commit/no-push boundary.

A policy file is not permission to inspect or rewrite adjacent repositories, tools, hooks, configs, credentials, device state, or candidate code.

## Workflow

1. Read only the named files and the named review artifact, if any. Do not use broad recursive search.
2. Bind every path as an absolute native path. Snapshot bytes, SHA-256, BOM, LF/CRLF counts, and literal marker counts before the first write.
3. Inspect the exact anchor and the relevant pointer/remediation wording. Preserve unrelated staged, dirty, and untracked paths.
4. Patch with unique surrounding context. Prefer a single canonical block and short pointers; do not restate the full policy in adapters.
5. For a marker required to occur exactly once, use one literal marker line rather than identical start/end markers containing the same token. Recount literal occurrences after the final write.
6. Keep the existing EOL convention. Never rewrite a whole file merely to normalize line endings.
7. Treat the first three investigation iterations as a feasibility gate: anchor discovery, behavior/precedence contract, and offline verification design. If the scope cannot be completed safely within the stated call budget, stop before a partial write and report the exact blocker plus a smaller proposed contract.
8. After the last edit, independently re-read all five classes of evidence: live target bytes, marker/pointer counts, exact diff, diff check, and numstat. Earlier checks are stale after any later write.

## Canonical-policy pattern

Put substantive precedence in one canonical source. Pointer files should say where the source is and that it wins on conflict; they should not duplicate the decision table. Separate implementation Worker and Reviewer roles. A worker's self-report or exit code is evidence to inspect, not approval. If a policy names a closeout gate, keep reviewer approval bound to the actual gate route and exact current bytes.

## Evidence and release boundary

Run tests/review with the same interpreter/executable. Import, collection, or native-dependency failure invalidates earlier evidence and is fail-closed. A release action is allowed only when the active canonical contract explicitly permits it and its complete gate passes. For a documentation-only task with an explicit no-commit/no-push rule, verification must remain read-only.

If the candidate directory is not a Git repository, do not fabricate `git diff` or `git numstat` output and do not guess a sibling repository. Report the exact Git binding limitation and still provide file-level evidence that is actually available.

## Final checklist

- [ ] Only exact allowlisted files changed.
- [ ] Canonical marker/block appears exactly as required.
- [ ] Each pointer file has one pointer and no duplicated policy.
- [ ] Dead skill references are corrected only when in scope.
- [ ] EOL/BOM and unrelated bytes are preserved.
- [ ] Final marker counts and pointer checks ran after the last write.
- [ ] `git diff --check` and `git diff --numstat` output is real, or the missing Git root is explicitly reported.
- [ ] No commit, push, config, credential, device, or candidate-code mutation occurred when forbidden.

## Pitfalls

- Do not use a start/end marker pair when acceptance counts the marker token literally; it creates a false duplicate.
- Do not let a broad skill or stale plan expand a five-file policy task.
- Do not claim final verification from a pre-edit snapshot.
- Do not repair a missing Git root by scanning the drive or selecting a similarly named repository.
- Do not turn Claude CLI or another advisor into an implicit implementation worker; preserve the user's explicit role boundary.

See `references/policy-allowlist-evidence.md` for the compact byte/EOL/marker evidence recipe.
See `references/canonical-policy-closeout-hardening-20261005.md` for the canonical-precedence policy pattern, Claude CLI wrapper arguments (-Mode Plan requires -PlanFile), and anti-surrender closeout remediation rules.
