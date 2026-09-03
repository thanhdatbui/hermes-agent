# HANDOFF.md Fleet Trim — Operational Procedure (proven 2026-08-11)

Class of task: user says "dọn HANDOFF ở cấp độ all repo" / "trim HANDOFF giữ current-state".
Same family as rule-file-append (EOL discipline) but for CUTTING resolved history out of
current-state files across a repo fleet. History is never lost: git keeps old versions.

## What to keep vs cut (per file)

Keep (current-state):
- Header lines (`# HANDOFF.md` + workflow-rules pointer)
- Rule/policy entries with recent dates (e.g. 2026-08-08..08-11: "2-MÁY FARM", "RULE 3 BƯỚC",
  "coordinate fallback sau UI recovery ladder", "Active Audit Routing Policy v6")
- `Workspace` / `Current Status` / `Current State` / `Blockers` / `Next Task` /
  `Safety Notes` / `Latest Artifacts` / `Latest Commit` / `Preset` sections
- ANY section with live blockers (FINAL_BLOCKED / handoff / do-not-touch lists) — these are
  operational truth, not history

Cut (resolved history):
- `## Latest Handoff Snapshot (2026-07-xx / 08-02 / 08-04 ...)` blocks — pure history
- Old per-batch recovery narratives with a terminal result (SUCCESS / FINAL_BLOCKED + ledger)
- Sections whose rule text already lives in AGENTS.md / PROJECT_RULES.md (the rule file is
  canonical; HANDOFF just needs the pointer)

## Procedure (EOL-preserving, backup-first)

1. **Map sections first.** Python: split lines, print `## `/`### ` headings with line numbers.
   Read the current-state block of each file before deciding cut lines.
2. **Define KEEP ranges** (1-based inclusive line ranges) per file in a dict. For small files
   (< ~250 lines) with no distinct history block: skip entirely.
3. **Backup + trim in ONE script**:
   - `splitlines(keepends=True)` — preserves each line's EOL byte-for-byte (CRLF/LF/MIXED
     all safe; NEVER write via text mode).
   - `attrib -R -H <file>` BEFORE writing — many HANDOFF.md are hidden+readonly →
     `PermissionError` otherwise (same as PROJECT_RULES.md).
   - Backup each file to `D:\Taadaa\handoff-trim-backup-<ts>/<repo>__HANDOFF.md` BEFORE the
     write.
   - Concatenate kept ranges, write bytes, assert kept count == sum of range sizes.
4. **Verify**: per file — line count == expected; EOL class unchanged; kept first-lines still
   present in new content. Read head+tail of each trimmed file to eyeball continuity.
5. **Commit gate**: stage ONLY `HANDOFF.md` (+ the PROJECT_RULES.md rule append if doing the
   rule in the same pass), commit message tiếng Việt, pull --rebase --autostash, push.
   Watch: repo may track `handoff.md` (lowercase) — `git add` the on-disk name.

## Pitfalls (all hit 2026-08-11)

- **Sequential trim + mid-fleet failure = double-trim.** Script trims files in order; if it
  dies at file N (e.g. PermissionError before attrib fix), files 1..N-1 are ALREADY trimmed.
  Re-running the same script then hits `range out of bounds` asserts on those files (their
  line count no longer matches original ranges). Fix: restore already-trimmed files from the
  backup dir first, then re-run the full plan once. Verify by line count after restore
  (`1309 lines` etc.) before re-running.
- **Git filename case mismatch.** `Tiktok_Reg` tracks `handoff.md` (lowercase); `git status
  --short -- HANDOFF.md` shows nothing (path mismatch) → looks like "not modified" when it is.
  Check with `git status --short` and grep -i, or `git add` the exact on-disk name.
- **`.git/FETCH_HEAD` hidden → pull/push fail.** Some repos have `FETCH_HEAD` with Hidden
  attribute → `cannot open '.git/FETCH_HEAD': Permission denied`. Fix: `attrib -R -H
  ".git/FETCH_HEAD"` then pull/push. (git fsmonitor--daemon running is NOT the cause.)
- **Dirty repos block `pull --rebase`** → use `--autostash` (keeps unrelated dirty files
  stashed+restored). Repos are often already dirty from other workstreams.
- **Append rule + trim in same pass**: do the PROJECT_RULES.md rule append first
  (rule-file-append skill), then trim HANDOFF, then one commit per repo containing both files
  (or two commits; keep scope explicit).

## Extended scope (2026-08-12): trim AGENTS.md + PROJECT_RULES.md too

The fleet trim was widened beyond HANDOFF.md to cut workspace-wide DUPLICATE policy blocks
from `AGENTS.md` and `PROJECT_RULES.md` (the biggest context bloat after HANDOFF history):

### AGENTS.md — cut duplicated workspace policy
- Remove the `<!-- CODEX-DIRECT-WORKER-POLICY:START/END -->` block (coordinator→worker
  boundary) and the `# AI Agent Workflow Rules` section. These are canonical in root
  `D:\Taadaa\AGENTS.md`; per-repo AGENTS.md only needs project-specific recovery contract +
  safety + context.
- Keep-ranges approach: find `CODEX-DIRECT-WORKER-POLICY:START` → `:END` line indices, add to
  remove-set; find `# AI Agent Workflow Rules` heading → EOF, add to remove-set; write kept =
  all lines NOT in remove-set. One script over all 16 repos works.
- EOL gotcha: if a file's original EOL is LF, force-written CRLF → "MIXED". Detect original
  EOL class and preserve it (for AI-Tools LF was original; re-write as LF not CRLF).

### PROJECT_RULES.md — cut workspace-wide duplicate tail blocks
- Remove trailing duplicate policy sections identical across repos:
  `## Merge / Cleanup Rule`, `## Giữ màn thật`, `## RULE 3 BƯỚC FIX`, `## COMMIT GATE`.
  Keep project-specific rules + `## HANDOFF.md Trim Rule` + `## Canonical Script Reuse Rule`.
- Gains are small (~40 lines/repo) because these blocks are short; PROJECT_RULES.md is mostly
  project-specific so do NOT deep-cut it. Skip files whose only bloat is project-specific.
- `open claw/PROJECT_RULES.md` has a different structure (Project Identity, Source Of Truth…)
  with no clear duplicated tail — skip it.

### Dual identical files: HANDOFF.md + handoff.md
- Some repos commit BOTH `HANDOFF.md` and `handoff.md` with IDENTICAL content (Tiktok_Reg).
  Trim the keep-ranges on the ORIGINAL once, then write the SAME trimmed bytes to both files
  (read HANDOFF.md after trim and copy to handoff.md). Do NOT re-run the range plan against
  `handoff.md` separately — its line count already changed and the range assert will fail.
- Verify both files end IDENTICAL (sha256 equal) after writing.

## Lost-original recovery (2026-08-12 pitfall — HIT)
- If a trim script writes the trimmed file THEN copies it to backup (wrong order), the backup
  is already trimmed → original 452-line version is lost from the backup dir.
- Recovery paths, in order:
  1. **Other backup dirs**: glob `D:/Taadaa/handoff-trim-backup-*/` for `*<Repo>*` and check
     sha256/size for the pre-trim line count. Earlier dated backups (e.g.
     `handoff-trim-backup-20260811-232921`) may still hold the original.
  2. **Git history**: `git -C <repo> log --oneline -- <file>` (may be empty if file was
     untracked/dirty and never committed). Check `git cat-file -p HEAD:<file>` + reflog.
  3. **Git dangling blobs** (works even if file was never committed): `git -C <repo> fsck
     --lost-found`, collect `dangling blob <sha>`, then for each: `git cat-file -p <sha>` and
     grep first line for the expected H1 (e.g. `TikTok ADB Registration - Handoff`). Save the
     matching blob. This recovered a 452-line original that was never in any commit.
- Lesson: always `copy2(SRC, BACKUP)` BEFORE the write in the trim script. And keep multiple
  dated backup dirs rather than overwriting one.

## Rule text appended to PROJECT_RULES.md (15 repos, 2026-08-11)

```
## HANDOFF.md Trim Rule (bắt buộc, 2026-08-11)
- HANDOFF.md là tài liệu current-state: giữ MỤC ĐÍCH project, state đang dở, blocker thật,
  bước tiếp theo an toàn, safety rules quan trọng, pointer tới lịch sử (reports/ hoặc git
  history). KHÔNG tích lũy entry đã resolved.
- Ngưỡng trim: HANDOFF > ~250 dòng → task/session kế phải TRIM: giữ top current-state +
  pointer, xoá phần resolved cũ khỏi file (git đã giữ bản cũ, không mất gì).
- Khi append entry mới mà file sắp vượt ngưỡng: trim entry cũ đã resolved cùng lượt, không
  để HANDOFF phình vô hạn.
- Giữ EOL khi sửa HANDOFF (append/trim bằng python, không patch LF).
```
