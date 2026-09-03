# Worked example — applying a 9-finding MINOR_FIXES audit round (consumer-recovery-migration plan, 2026-08-12)

Session shape: PLAN-ONLY edit of ONE plan file (`automation-core\.hermes\plans\2026-08-12_consumer-recovery-adapter-migration.md`, 490 lines) per an AG Opus MINOR_FIXES audit (`reports\ag-audit\consumer-migration-plan-response.txt`). No source/test/config/consumer edits, no commit, no live/ADB/credential/workbook/log. Outcome: 490 → 502 lines, 13 sequential same-file patches, final verification cycle passed.

## Finding → fix pattern (what a "verify-then-write" round looks like)

| Audit finding | Verified BEFORE writing | Plan change |
|---|---|---|
| 1.1 §15 "Phase count: 12" wrong | Counted phases: Phase 0 + P1–P9 + P10 = 11 | §15 → 11; grep whole file for `Phase count: 12` → 0 hits |
| 2.3 RED step claims 0.4.44 lacks escalation.py (may be false) | `unzip -l` on real wheels: 0.4.18 wheel (`/d/CodexRuntime/automation-core-popup26-wheel-20260802/`) has `recovery.py`, NO `escalation.py`; 0.4.44 wheel in `dist/` also has NO escalation entry; 0.4.24 wheel NOT in `dist/` → NOT_INSPECTED | RED retargeted to REAL artifact 0.4.18 with fallback clause (artifact gone → ghi NEEDS_PROOF, không fake RED); §14 risk bullet synced |
| 1.3/10.3 P10 "runtime-connected" over-claims; registry scan underspecified | — (design clarification) | "runtime-connected" defined = import + registration + runtime seam via focused offline fake/artifact; live exercise marked NEEDS_PROOF separately; probe = concrete offline script with provenance assert + redacted manifest (consumer, commit, pin, adapter module, classes, hook, test IDs, VERIFIED_OFFLINE/NEEDS_PROOF, sha256) |
| 3.2 P1 allowlist includes speculative files | — | Split "discovery read-only candidates" vs "patch allowlist finalized after discovery"; 3 speculative files explicitly NOT pre-approved |
| 4.4 Tiktok_Reg REQUIRED_CORE_VERSION "xác nhận lại" ambiguous | — | Decision locked: update 0.4.43 → 0.4.45 (pin target), add version-gate test file to allowlist; removed hedge in §9 too |
| 8.3 no baseline suite counts | — | §12 new mandatory step 2: baseline focused/full suite BEFORE any write (command + exact pass/fail/error + pre-existing classification); commit gates reference "so với baseline mục 12.2" |
| 4.6 P9 new adapter filename collision | — | Named `scripts/tiktok_workflow/recovery_adapter.py` explicitly (existing `adapter.py` read-only), discovery may adjust |
| 7.1 M1/M6 vs stop conditions contradiction | — | M1 = TARGET (goal, not achieved fact); M6 + §13.6 + P10 gate: N/9 VERIFIED_OFFLINE + K NEEDS_PROOF/DISPOSITION; STOPPED consumer blocks final acceptance until disposition; never call "complete" |

## Key commands that grounded the edits

```bash
# wheel-content probe (name-only, safe — no extract/install/site-packages)
unzip -l /d/CodexRuntime/automation-core-popup26-wheel-20260802/automation_core-0.4.18-py3-none-any.whl | grep -E '\.py$'
unzip -l dist/automation_core-0.4.44-py3-none-any.whl | grep -E '\.py$'
# stale-phrase sweep AFTER edits (expect 0, or only intentional negations)
grep -c 'Phase count: 12' <plan> ; grep -n 'runtime-connected' <plan> | grep -vE 'offline|định nghĩa|NEEDS_PROOF'
grep -n 'xác nhận lại' <plan> | grep -v 'không để'
# final verification cycle
wc -l <plan> ; sha256sum <plan> ; git status --short --untracked-files=all
```

## Mechanics that mattered

- **Same-file patches serialized** — 13 sequential `patch` calls, one per turn; never batched parallel writes to one file.
- **git -C /d/... failed** (`fatal: cannot change to '/d/Taadaa/automation-core'`) even though `/d` exists — used `workdir=/d/Taadaa/automation-core` + plain relative `git status` instead.
- **Stale wording repeats outside the audit's cited locator** — e.g. finding 1.1 cited §15, but "runtime-connected"/"9/9 hard gate" phrasing lived in M1, M6, §13.6, P10 mục tiêu, P10 audit gate, §14; each fix swept the whole file.
- **Finding IDs embedded in plan prose** (`MINOR 4.4: ...`, `MINOR 3.2 — ...`) so the next auditor can grep plan ↔ audit 1:1.
- **Final report by locator** with exact line numbers, line-count delta (490→502), SHA256, and `git status` evidence (only 2 pre-existing untracked plans; no tracked modified; HEAD unchanged).

## Verification evidence (final)

- File: `D:\Taadaa\automation-core\.hermes\plans\2026-08-12_consumer-recovery-adapter-migration.md`
- 502 lines, SHA256 `6d2e6bd75d4809e45ec2a3e207acd634069a9b8bf000c8bba65345689cbef218`
- `git status`: `?? .hermes/plans/2026-08-11_ai-escalation-failed-locked.md` + `?? .hermes/plans/2026-08-12_consumer-recovery-adapter-migration.md` only; no tracked modified; HEAD `8a3ede5` unchanged; no commit.
