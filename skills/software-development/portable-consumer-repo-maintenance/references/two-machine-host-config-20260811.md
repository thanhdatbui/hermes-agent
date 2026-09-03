# Two-machine host-config build (2026-08-11)

Shipped `taadaa_host.py` into Tiktok-video, tiktok-luot nuoi acc, Tiktok_Reg.
Commits: 35bc940 / fdd66b3 / 11a70c8 (remotes verified).

## Layout
- Canonical module: `D:\Taadaa\tools\taadaa_host.py` (LF).
- Copies per repo, converted to repo EOL (CRLF). Drift check:
  `python D:/Taadaa/tools/check_taadaa_host_copies.py` (normalizes EOL, sha256).
- Per-machine YAML: `D:\Taadaa\machine-config\kibe.yaml` (range 1-80),
  `admin.yaml` (range 200-999). Not in git; template lives in repo.
  **host_id = tên PC THẬT (kibe = PC này, admin = PC kia)** — user bác bỏ
  `farm-a`/`farm-b` abstract ("K dùng farm A. Dùng kibe và admin"), rename
  commit c138c8f / a6a7dd7 / 2fc2da8 sau audit rename APPROVED. Khi chọn
  host_id đừng đặt tên trừu tượng — hỏi/dùng tên máy thật ngay từ đầu.
- OneDrive partition: `D:/OneDrive/TaadaaData/{kibe,admin}/` +
  `TaadaaData-Snapshots/` (retention ~7 days, outside live tree).
- Workbooks máy A KHÔNG được move (đang chạy hằng ngày); host config trỏ tới
  chúng qua `TAADAA_HOST_CONFIG_FALLBACK` hoặc legacy env.

## Module contract (fail-closed)
- `load_host_config()`: TAADAA_HOST_CONFIG unset/invalid → HostConfigError.
  Validates host_id ∈ {kibe, admin}, range increasing, workbook_root dir
  exists, runtime_root OUTSIDE OneDrive.
- `_is_onedrive_path`: env roots first (OneDrive/OneDriveConsumer/
  OneDriveCommercial → commonpath), path-part fallback. Mount/symlink safe.
- `host_guard()`: entry helper. Env set → validated dict; unset → LOUD stderr
  "RUNNING IN LEGACY MODE — host guard DISABLED" + None. Máy A keeps working,
  never silent.
- `assert_machine_in_range(machine, host)`: outside range → HostConfigError
  BEFORE any device action.
- `resolve_workbook(host, filename)`: candidate must stay under workbook_root.
- `apply_env(host)`: sets TIKTOK_REG_TRACKING_WORKBOOK / SOURCE_WORKBOOK /
  TARGET_INVENTORY_WORKBOOK / RUNTIME_ROOT / ARTIFACT_ROOT. Host config WINS
  over stale env override (warns, replaces, never setdefault).

## Injection points
- Tiktok-video `scripts/tiktok_workflow/run_post.py`: after `Config(args.config)`
  → `host_guard()` + `assert_machine_in_range(int(args.machine))` (only when
  args.machine set).
- tiktok-luot `python_runner/run_tiktok.py` main(): after arg validation →
  import taadaa_host (ImportError → None), guard each `--machines` part.
- Tiktok_Reg `project_paths.py`: at module import, BEFORE `_CANONICAL_*` /
  `_configured_workbook_path` resolve → `host_guard()` + `apply_env()`.
  ImportError → legacy (canonical paths cũ).

## Audit flow used (AG Opus, read-only)
1. Plan audit (`.hermes/plans/plan-2-may-host-config.md`) → MINOR_FIXES:
   (1) OneDrive detect via env root, (2) multi-copy drift → check script,
   (3) legacy mode must be LOUD, (4) apply_env once at entry before subprocess.
   NIT: backup machine-config, snapshot retention.
2. Fixed all; re-audit the FULL staged diff (3 repos concatenated into one
   prompt `audit-prompt-diff.txt`) → APPROVED body, but wrapper printed
   `AG_AUDIT_VERDICT=UNPARSEABLE` vì response starts with `## VERDICT` heading,
   not a bare token. Lesson: read the response file; body APPROVED counts.
3. Tests: `test_taadaa_host.py` 7 fail-closed cases, 7/7 in all 3 repos
   (note _path_setup import for tiktok-luot tests dir).

## Pitfalls
- Stale env `TIKTOK_REG_*` already exported (pointing máy A canonical paths) —
  apply_env must OVERRIDE, else admin (máy B) corrupts kibe (máy A) workbooks.
  Phát hiện: `env | grep -i TIKTOK_REG` trước khi test — session env của Hermes
  có thể mang sẵn các biến này từ profile/user env, không phải do script set.
- `except (mod.HostConfigError, ImportError)` NameError when import fails
  (mod unbound) → import in own try, `mod = None`.
- `git add <file>` stages whole working-tree file; Tiktok_Reg commit carried a
  pre-existing `_configured_workbook_path` refactor. OK only because audit
  prompt contained the full `git diff <file>` (capture diff BEFORE editing).
- MSYS heredoc `python - <<'PY'` mangles backslash strings (SyntaxError
  unterminated string literal) — write helper .py via write_file, run, delete.
- `git pull --rebase` fails with "unstaged changes" on dirty repos; push still
  OK if remote hasn't moved (fetch first to confirm). Don't stash/commit foreign
  dirt just to satisfy the rebase gate.
- Windows case-insensitive FS: HANDOFF.md == handoff.md (same file) — check
  `git status` for the tracked casing before appending docs.