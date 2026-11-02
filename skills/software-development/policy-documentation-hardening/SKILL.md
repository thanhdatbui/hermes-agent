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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
