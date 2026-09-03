# Farm-wide workbook path-migration audit (phase 3, 2026-08-12)

Trigger: user moved the workbook root (e.g. all workbooks → `D:\OneDrive\TaadaaData\kibe` for máy kibe) and wants every script in every automation repo checked/fixed for stale old-path references.

## 1. Verify destination inventory first

```bash
ls -la /d/OneDrive/TaadaaData/kibe/ | grep -i xlsx
```

Expected set (kibe): `Tik1.xlsx`, `Tik2.xlsx`, `tik3.xlsx`, `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `gmail_clean_v2.xlsx`, `PROXYgandienthoai.xlsx` (+ `.bak` files).

- Missing workbook = broken move even if no script references it (observed: Tik2 missing; scripts only used Tik1, so a script-only scan would pass a broken move).
- Check stray duplicates: `ls /d/*.xlsx` (observed `D:\Tik2.xlsx` at drive root — report, don't delete without asking).
- Old folders may still exist with the originals — don't delete them during the audit.

## 2. Enumerate repos

```bash
cd /d
for d in automation-core Tiktok_Reg tiktok-log-in tiktok-follow \
         tiktok-add-bao-mat-f2a gan-proxy; do \
  [ -d "/d/Taadaa/$d/.git" ] && echo "GIT: $d"; done
```

Git repos under `D:\Taadaa`; PLUS non-git `D:\CodexRuntime\tiktok-video` (m74) — rollback for it = local backup dir, no `git checkout`.

## 3. Scan pattern (timeout-safe)

Full-tree `rg -n` times out (120s) on `batch-runs/` + `stale-lock-archive/` + `runs/` (thousands of lock/report JSONs). Two-phase approach:

Phase A — files-only, per repo, heavy excludes:

```bash
cd /d && for r in Taadaa/automation-core Taadaa/Tiktok_Reg Taadaa/tiktok-log-in \
  Taadaa/tiktok-follow Taadaa/tiktok-add-bao-mat-f2a Taadaa/gan-proxy \
  CodexRuntime/tiktok-video; do
  echo "=== $r"
  rg -l -i --hidden -g '!.git/**' -g '!__pycache__/**' -g '!*.pyc' \
    -g '!node_modules/**' -g '!*.md' -g '!*.jsonl' -g '!*.log' \
    -g '!reports/**' -g '!.ai-runs/**' -g '!artifacts/**' -g '!tasks/**' \
    -g '!.hermes/**' -g '!*backup*' -g '!*.bak*' \
    'OneDrive[\\/]Tiktok|OneDrive[\\/]Tiktok_Reg|codex_gmail_debug|TIKTOKTaiKhoan|[\\/]Tiktok Tài Khoản|D:[\\/]Tiktok[\\/]' "$r"
done
```

Phase B — read matched files directly (never re-scan the tree). For `.runtime/**`, `venv*/**`, `batch-runs/**`, `stale-lock-archive/**`, `runs/**` add to excludes — they are history, not live code.

Old-path pattern set (this farm):
- `OneDrive[\\/]Tiktok` — old Tik1/2/3 root
- `OneDrive[\\/]Tiktok_Reg` — old REG data root
- `codex_gmail_debug` — old gmail/safe-workbook roots (but see classification below)
- `D:[\\/]PROXYgandienthoai` — old proxy-map root
- `Tiktok Tài Khoản`, `TIKTOKTaiKhoan` — older workbook roots
- `Tik[123]\.xlsx`, `taikhoan_dat_v2`, `taikhoan_run_safe`, `gmail_clean_v2`

## 4. Classify matches

| Match | Action |
|---|---|
| Script/config workbook path (`.py` `.mjs` `.yaml` `.ps1` `.bat` `.json` config) | FIX → `D:\OneDrive\TaadaaData\kibe\...` |
| `D:\CodexRuntime\codex_gmail_debug-*` | LEAVE — runtime artifact root, not a workbook |
| GemPhoneFarm data (`data/*.gemphonefarm`, `*_decrypted.json`) | LEAVE — workflow data embedding `defaultValue: "D:\Tiktok Tài Khoản\Tik3.xlsx"`; exclude `data/**` from fix pass, report separately |
| `batch-runs/`, `stale-lock-archive/`, `runs/`, `artifacts/`, `.runtime/` | EXCLUDE from scan — history/locks |
| `google_health.py` etc. matching `gmail_clean_v2`/`taikhoan_dat_v2` as column/log names | LEAVE — not paths |
| `*lock.json` command strings embedding old `--mapping` | EXCLUDE — historical lock records |

## 5. Fix pass

- Baseline BEFORE editing: per repo `git rev-parse --short HEAD` + `git status --porcelain` (repos are often pre-dirty — your delta must be provably yours). Non-git trees: `mkdir -p /d/tmp/<task>-baseline-<date>` + `cp` originals.
- `patch` tool is fine for single-line path swaps (worked on 15 files here); verify each diff, and `py_compile` every edited `.py` (`python -m py_compile f1 f2 ...`).
- Update tests that assert canonical paths in the SAME pass: `test_project_paths.py`, `test_cli.py` — then re-run them.
- Also fix script-referenced `.bak` files: `edit_tik1.mjs` loaded `sourceBackup = Tik1.xlsx.bak_before_restart_20260720T040750Z` that lived only in the old folder → copy the backup into kibe AND update the reference.
- Config YAML: double-quoted Windows paths need `\\` per separator — keep the file's existing escaping style (`"D:\\OneDrive\\TaadaaData\\kibe\\taikhoan_run_safe.xlsx"`).
- Env files (`.env.local.ps1`): update ALL aliases (`TIKTOK_REG_DATA_DIR`, `SOURCE`, `TRACKING`, `PROXY_MAP`, `SAFE`, `TIKTOK_SAFE_WORKBOOK` etc.) — one stale alias = one stale path.

## 6. Verify

- Re-scan with the phase-A command restricted to live dirs; expect exit 1 (no matches) for workbook-path patterns. Split into per-repo loops to avoid one big timeout.
- `py_compile` all edited Python.
- Run edited test files: `python -m pytest tests/test_project_paths.py -q` and `tests/test_cli.py -q` (5+5 passed here).
- Report: files fixed per repo, files copied (workbooks + backups), what was deliberately LEFT (runtime roots, GemPhoneFarm data, history), commit status (uncommitted — 4 repos dirty), and the rollback path (git HEADs + `D:\tmp\path-fix-baseline-20260812\`).

## Cross-host safety note

`project_paths.py` canonical fallbacks changed to kibe are safe for admin máy B: `TAADAA_HOST_CONFIG=admin.yaml` + `apply_env()` overrides env-driven workbooks per host, so a kibe canonical never feeds máy B. Host-config wins over stale env (loud warning on replace).
