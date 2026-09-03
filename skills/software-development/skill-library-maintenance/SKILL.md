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

## Hard constraints

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

## Merge duplicate skills

1. Read BOTH skills fully; map headers of each.
2. **Copy the source skill's `references/` files into the target FIRST** (before deleting anything) — `cp` or `skill_manage write_file`.
3. When the two skills contradict each other, resolve from PRIMARY SOURCES — real repo code, live source files, current config — never by picking one skill's claim. (Session examples: Hotmail entrypoint legacy-vs-live resolved by reading `change_info_hotmail.py` imports; `/model` parens "provider order" vs "model count" resolved by reading `plugins/platforms/telegram/adapter.py:5150`.)
4. Patch the target with the source's unique content (compact; drop stale content the target already supersedes — mark the resolution in a short note).
5. Delete the source: `skill_manage(delete, absorbed_into=<target>)` — updates downstream tooling.

## File-surgery safety (PITFALL — destroyed a file)

- NEVER `open(path, 'wb')` before the full payload is built: if the write expression throws AFTER the open, the file is already truncated to 0 bytes. Real incident: a TypeError after `open('wb')` zeroed `tiktok-upload-ui-recovery/SKILL.md`.
- Correct pattern: build the ENTIRE output (bytes or string) in memory first, then a single `open(path,'wb').write(payload)`. Back up before any surgery (`cp f f.bak-<ts>`). Ready-to-run one-shots (restore + trim): `references/surgery-patterns.md`.
- **Restore a destroyed file** from the persisted tool output cache: `~/AppData/Local/hermes/cache/terminal/hermes-results/<call>.txt` holds the FULL original tool result as JSON — extract the `content` field, convert EOL, write back. Verify integrity: restored byte size must equal the `file_size` recorded in the first read; keep a sha256 of the restored state for the audit.

## Junction gotcha (local skills ↔ sync git repo)

Some local skill dirs are JUNCTIONS into a sync repo (e.g. `autonomous-ai-agents/agent-review-loops` → `D:\Taadaa\Hermes\skills\...`, wired to the `sync-hermes-skills-to-git` cron). Symptoms: `cp local repo` errors "are the same file"; local edits appear as `git status` changes in the repo; deleted local skills still exist in the repo tree.
- Check with `os.path.realpath(local) == os.path.realpath(repo)` before copying.
- When syncing to git: `git add`/`git rm` ONLY the changed skill paths — the repo carries unrelated modified files from other workstreams (never `git add skills/` blindly); commit with a Vietnamese message per user convention; push to the fork remote.
- **Cron auto-commit trap:** the sync cron (`sync-hermes-skills-to-git`, every 30m) runs `git add <2 synced skills>` + `git commit` + push — and `git commit` takes EVERYTHING already staged. Real: 13 half-staged files were committed+pushed as "chore: sync orchestration skills" (1ab0af66) mid-work; the index looked mysteriously empty right before my own commit. Don't leave staged-but-uncommitted work in `D:\Taadaa\Hermes`; if the index is unexpectedly clean, check `git log -1 --stat` — the cron likely already committed your files (content correct, message is the cron's).

## Audit gate (user protocol)

- After finishing a consolidation batch: run an independent audit (Claude Opus `ag/claude-opus-4-6-thinking`, high reasoning) with a self-contained manifest: each change, how conflicts were resolved (with primary-source citations), sizes before/after, and evidence (hashes) for any restore claims.
- Iterate: MINOR_FIXES → fix findings → re-audit (SAME model, no switching between rounds) → APPROVED. Log the verdict line + per-change OK/FINDING table.
- **Long audit prompts (>10KB) go via `curl --data @bodyfile.json` to 9router** — the PowerShell `invoke-ag-audit.ps1` wrapper hangs past its timeout on long prompts (details + body recipe: `9router-proxy-ops` → "Hermes-side specifics" / AG wrapper section).
- **Write the manifest with `write_file`, never inside a python heredoc in terminal:** backslash-heavy content (`C:\...`, `D:\...` paths) inside a heredoc python string throws `SyntaxError: truncated \UXXXXXXXX escape` and wastes a round. Pattern: `write_file` the manifest → tiny python reads it and `json.dumps` the body → curl `--data @body.json`. Parse the response with the multi-JSON `parse_all` (9router streams fragments) — save the content to a file, then `read_file` it.

## Pitfalls

- Deleting a merged-away skill before copying its `references/` = permanent content loss. Copy first, delete last.
- Trusting one skill's claim over another's on a conflict → resolve from primary source, and write down WHICH side was wrong (future audits check this).
- Trimming by hand-editing with `sed`/`awk` on CRLF files → EOL mangling; use python split/join on the detected EOL.
- Not backing up before multi-step surgery on a skill at/near the cap.

## Verification checklist

- [ ] All source skills' reference files exist under the target skill
- [ ] Conflicts resolved with primary-source evidence; resolution note in the target
- [ ] Deleted skills reported `absorbed_into=<target>`
- [ ] Edited SKILL.md char counts all < 100,000 (aim < 90K)
- [ ] EOL preserved on CRLF files; `file f` check
- [ ] Audit loop reached `VERDICT: APPROVED`
- [ ] Git repo synced: only changed skill paths staged/committed/pushed
