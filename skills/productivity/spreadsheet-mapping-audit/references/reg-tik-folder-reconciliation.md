# REG/Tik folder reconciliation reference

## Contract discovered

- Authoritative registration workbook: `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx` (note the space before `.xlsx`), sheet `Tài Khoản`.
- Relevant columns: `Máy`, `Folder Video` (renamed from `Tik` at user request — values identical), `ID`, `device ID`.
- `Tik` / `Folder Video` is a global numeric asset/folder key, not the account ordinal within a machine.
- Media path contract used by the upload workflow: `D:\TIKTOK-videonuoinick\{Folder Video}\{video number}.mp4`.
- Derived workbooks: `D:\OneDrive\Tiktok\Tik1.xlsx`, `Tik2.xlsx`, `tik3.xlsx`; sheet `TaiKhoan`; account `ID` is column 3, `Folder Video` is column 4.
- Slot mapping: `Tik1` = k=1, `Tik2` = k=2, `tik3` = k=3 slots of each machine.

## Folder allocation formula (discovered 2026-08-11)

```
Folder Video(machine m, slot k) = (m - 1) * 8 + k
```

- Tik1 (k=1): 1, 9, 17, 25, 33, ... 633
- Tik2 (k=2): 2, 10, 18, 26, 34, ... 634
- tik3 (k=3): 3, 11, 19, 27, 35, ... 635 (not rendered yet)

Evidence the formula is correct:
- `D:\TIKTOK-videonuoinick` contains exactly 160 folders = 80 machines × 2 slots (1, 2, 9, 10, 17, 18, ... 633, 634) with >=44 MP4 each — precisely Tik1+Tik2 folders; Tik3 folders absent.
- Tik1 original (the workbook whose videos were actually posted) had folder = (m-1)*8+1 with **zero mismatches** across all 80 machines.
- Render manifests `runs/tik2-kibe-m*-src*-out*/render_manifest.csv` show outputs exactly equal to (m-1)*8+2 (out 2, 10, 18, ... 634); `run_meta.json` args confirm `--randomize`, `preset_owner.json`, slot.

## Why raw REG folder values cannot be trusted

REG `Tik`/`Folder Video` cells were corrupted by earlier manual row edits (July 2026): e.g. machine 2 read `12, 10, 11, 13, 14, 15` instead of `9, 10, 11, 12, 13, 14`; machine 10 read `73, 75, 76, ...` instead of `73, 74, 75...`. Historical backups available in the same directory (`.backup-*`, `.codex-backup-*`, `.bak-*`) show the drift over time — always diff against backups before trusting the current file.

## Correct synchronization procedure

1. Back up all edited workbooks with a timestamped `.xlsx`-suffixed name (`.bak-<label>-<ts>.xlsx`; do NOT drop the extension — openpyxl refuses to open extension-less backups).
2. Read REG row by row, keyed by machine; preserve row position as slot index (an empty-ID row still occupies its slot).
3. Slot k target row gets: `ID` = REG row k of that machine (empty if none), `Folder Video` = `(m-1)*8+k` — computed, not copied from the corrupted REG cell.
4. Write to a temp file ending in `.xlsx`, close, reopen temp read-only, verify every row (`(machine,slot) -> (ID, Folder Video)`), then `os.replace` onto the target. Never save directly over the live file without this verify-at-temp step.
5. Recompute status/check columns (`OK` if ID present else `MISSING_ID`) — they are static text, not formulas.
6. Re-run the full audit and require zero unexpected mismatches.
7. Trust anchor-proven workbooks over the master when they disagree, and state the `old -> new` folder mapping to the user when renders already exist.

## Incident lesson

A prior repair synchronized IDs using non-empty-ID ordering (wrong: shifts later slots), copied corrupted REG folder values, and left stale `MISSING_ID` text. User corrected: "map theo Tik1, vì đã đăng video theo Tik1 rồi" — anchor on the posted workbook, use row-position slots, and compute folder by formula. Recovery: timestamped backups, temp `.xlsx` verify-then-replace, final audit 0 mismatches across all three derived files and REG.

## Reporting

Keep reports concise: state the key semantics, exact match counts per workbook, formula rule, and top failure classes. Do not print passwords, 2FA, mail passwords, or raw account credentials from REG.

## Render provenance check

When a derived workbook's folder mapping changes after rendering, compare the historical backup mapping with the current one and the renderer's run metadata before deciding the render was wrong. A valid run records source folder, output folder, preset, and randomization flags (see `run_meta.json` / `render_manifest.csv` under `D:\CodexRuntime\tiktok-video\runs\tik2-kibe-*`). Preserve old artifacts until the user explicitly chooses reconcile, rerender, or cleanup.