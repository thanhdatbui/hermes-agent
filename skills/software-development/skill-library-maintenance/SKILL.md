---
name: skill-library-maintenance
description: Maintain the Hermes skill library — audit duplicates, merge overlapping skills, trim SKILL.md past the 100K cap, restore damaged files, sync to the git repo, and pass the audit gate.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, consolidation, merge, trim, maintenance, audit]
    related_skills: [hermes-agent-skill-authoring, 9router-proxy-ops, tiktok-upload-ui-recovery]
---
# Skill Library Maintenance

Use when the skill library needs consolidation: duplicate/overlapping skills, SKILL.md files near the 100,000-char cap, merges of same-domain skills, or restoring a damaged skill file. Verified end-to-end 2026-08-09 (115 skills → 104, 9 merges, 1 trim, audit APPROVED).

References:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

## Session-derived improvement: runtime guard edits

When a session changes a guard/allowlist through an external coding agent, preserve the class-level workflow and record the session-specific path/verification details in a reference file rather than expanding the main skill with one-off filenames. The minimum evidence bundle is: exact live symbol/anchor, one-file diff, focused positive and negative gate tests, compile result, and a separate reload/cache assessment. Never treat a successful target script invocation or worker self-report as proof that the gate is active. See `references/fail-closed-completion-claim-detection.md` for the reusable completion-claim false-positive matrix and guard regression recipe.

- **SKILL.md ≤ 100,000 chars** (`MAX_SKILL_CONTENT_CHARS`). `skill_manage` rejects ANY patch above it — an oversized skill is UNEDITABLE until trimmed. Real incident: `tiktok-upload-ui-recovery` hit ~100.6K and every edit failed.
- Skill edits are durable: the user's rule is **finish work → independent audit → fix findings → re-audit until `APPROVED`** (same model every round; see Audit gate below).

## Trim an oversized SKILL.md

1. Map structure: `grep -n "^#" SKILL.md` + measure section sizes.
2. Pick the biggest / least-used / already-duplicated sections (e.g. content now owned by another skill after a merge).
3. Move the section VERBATIM into `references/<topic>.md` (create via `skill_manage write_file`), replace in SKILL.md with a 1-line pointer.
4. Preserve the file's EOL (farm skills are CRLF — byte-diff conventions).
5. Verify final char count (`len(new_txt)`) — target < 90K for headroom.
6. **Over-trim trap:** a move range like `'## Phase 3' → EOF` can grab the BULK of a long file (real: `research-paper-writing` moved 84K of 103K, leaving an 18.8K skeleton; audit flags P2-BALANCE). Before cutting, measure the summed size of the ranges — sanity-check they're NOT the majority of the file. Invariant after cutting: `kept_chars + moved_chars ≈ original_chars` (difference = pointer block only) — this is also your no-content-loss proof for the audit.
7. **Reconstruct after an over-trim** (no redo from scratch): original = current SKILL.md with the pointer block stripped + the moved lines from the reference file (the reference IS the backup), then re-cut with wider keep ranges.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
