# Tiktok_Reg batch runner — clean-environment runbook (2026-08)

Repo: `D:\Taadaa\Tiktok_Reg`. Runs TikTok registration (max 1 account per
machine) across the Samsung S7 farm using `automation-core` device locks.

## Eligibility rule (the user's canonical definition)

A machine is a target when `gmail_clean_v2.xlsx` has a source mail whose
TikTok ID is blank in `taikhoan_dat_v2_updated .xlsx` (tracking).
Exactly one account per machine. Implemented by:

- `scripts/tiktok_target_eligibility.py` — `load_source_rows()`,
  `load_registered_mailboxes()`, `select_pending_targets()` (max 1/STT).
- `_detect_clean.py` — read-only detector, writes the selection manifest.
- `_run_all_targets.py` — launcher: device lock + `build_machine_launch_plan`
  (stagger 2–8s, `MAX_WORKERS=40`), child `social_reg_v1.py <stt> --ss
  --defer-tracking-write`, workbook only via the deferred writer.
- `scripts/run_tiktok_recovery_new_handler.py` — the recovery runner used for
  targets that previously exhausted the old signature. Pins
  `REQUIRED_CORE_VERSION` and refuses to start on a version mismatch.
  `--full-scope-takeover` is required for reclaiming retained Tiktok_Reg
  locks; without it, cross-project locks are correctly skipped as
  `DEVICE_LOCKED` (policy forbids reclaiming another project's lock).

## The working invocation

`env -i` is required — the Hermes terminal PATH is polluted with the Hermes
venv. Keep HOME/USERPROFILE, prepend Python312, and set PYTHONPATH so both
`flows` (taadaa-hotmail) and repo scripts resolve:

```bash
cd /d/Taadaa/Tiktok_Reg
env -i HOME="$HOME" USERPROFILE="$USERPROFILE" \
  PATH="/c/Users/Kibe/AppData/Local/Programs/Python/Python312:/c/Windows/System32:/c/Windows" \
  PYTHONPATH="D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail" \
  PYTHONIOENCODING=utf-8 \
  "/c/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe" -u \
  scripts/run_tiktok_recovery_new_handler.py --max-workers 40
```

Detector first, into the runner's exact target-file path:

```bash
mkdir -p ".runtime/Taadaa/Tiktok_Reg/artifacts/pending"
TIKTOK_REG_TARGETS_FILE="$(pwd)/.runtime/Taadaa/Tiktok_Reg/artifacts/pending/tiktok_reg_clean_targets.json" \
  python -u _detect_clean.py
```

## Environment facts that bite

- **`flows` is not importable from a bare interpreter** — `social_reg_v1.py`
  does `from flows.hotmail_login import ...`; the package is an editable
  install of `D:\Taadaa\Hotmail`, so it only resolves when that dir is on
  `PYTHONPATH`. (`importlib.metadata.distribution("taadaa-hotmail")` resolves
  but its `locate_file` is the repo root, not a site-packages copy.)
- **`python` / `python3` in PATH resolve to the Hermes venv** (or a stub).
  Use the absolute Python312 path in `env -i`.
- **No `python3` for py3.12 in PATH under `env -i`** — hardcode the absolute
  path instead of relying on `python3`/`python`.
- **Artifact root is `.runtime\Taadaa\Tiktok_Reg\artifacts`** (LOCALAPPDATA
  override, not the repo `artifacts/`). Run dirs:
  `...\artifacts\runs\recovery-new-handler\<timestamp>\stt_<NN>\attempt_*`.
  Ledger per target: `recovery_ledger.json`; final: `recovery_summary.json`.
- **Cross-project locks**: `.codex\\device-locks\\machine_<n>.lock.json` may be
  held by `tiktok-upload`, `add mail khoi phuc`, `tiktok-luot nuoi acc` etc.,
  all with dead PIDs. Default policy: do NOT reclaim them — the lock API
  rejects cross-project takeover and that is the correct behavior.
  **Explicit user override (2026-08-05)**: the user authorized reclaiming dead
  cross-project locks for registration runs EXCEPT the `tiktok-upload`
  project, which stays untouchable. Ask the user before assuming this
  authorization; it is per-run, not global.
- **Legacy protocol-v1 locks cannot be reclaimed through the core API** —
  `_takeover_payload` requires `lock_protocol_version == 2`; locks written
  before the v2 protocol (field `lock_protocol_version: None`, e.g. old
  `add mail khoi phuc` / `tiktok-luot nuoi acc` handoffs) always raise
  `DeviceLockUnavailable` even with `FULL_SCOPE_TAKEOVER` +
  `takeover_authorized=True`. The only path for those is manual removal after
  proof: (1) confirm PID dead via `kill -0`, (2) confirm project ≠ protected,
  (3) back up the lock JSON into `.codex/device-locks/backup_takeover_<date>/`,
  (4) delete BOTH `machine_<n>.lock.json` AND `serial_<serial>.lock.json` (the
  serial twin also blocks the runner).

## Workbook header aliases needed by the eligibility parser

Source workbook `gmail_clean_v2.xlsx` (sheet `Gmail Accounts`) uses
Vietnamese headers: `số máy`, `tài khoản gmail`, `pass mail`. The parser's
`SOURCE_HEADER_ALIASES` must include `"tai khoan gmail"` (normalized
NFKD+casefold) or detection fails with `SOURCE_WORKBOOK_HEADERS_MISSING:
email`. Tracking workbook (`taikhoan_dat_v2_updated .xlsx`, sheet
`Tài Khoản`) headers: `Máy | Tik | ID | PASS | 2FA | GMAIL | PASS MAIL |
NGÀY THÁNG NĂM SINH | NGÀY TẠO | device ID`. The bare alias `"tik"` must NOT
be in the `tiktok_id` alias set, or `TRACKING_WORKBOOK_HEADERS_AMBIGUOUS:
tiktok_id` fires (column `Tik` collides with `ID`).

## Workbook write guard: TIKTOK_REG_WRITER_ID (2026-08-05)

The tracking workbook write path (`scripts/deferred_tracking_writer.py` →
`workbook_transaction_adapter.py` → `automation_core.workbook.
single_writer_workbook_update`) **fail-closes** unless BOTH env vars are set
and equal:

```bash
TIKTOK_REG_WRITER_ID=tiktok-reg-runner TIKTOK_REG_EXPECTED_WRITER_ID=tiktok-reg-runner
```

Without them, a fully-verified registration (profile XML/screenshot proof +
`tracking_result_*.json` with `status=SUCCESS`) ends as
`WORKBOOK_WRITE:BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking` — the
account is registered on-device but never lands in `taikhoan_dat_v2_updated
.xlsx`. Recovery is safe: re-run the apply tool against the saved
`tracking_result_*.json` with the env set:

```bash
env ... TIKTOK_REG_WRITER_ID=tiktok-reg-runner TIKTOK_REG_EXPECTED_WRITER_ID=tiktok-reg-runner \
  python -u scripts/apply_deferred_tracking_results.py \
  .runtime/Taadaa/Tiktok_Reg/artifacts/runs/recovery-new-handler/<ts>/stt_<n>/attempt_*/tracking_result_*.json
```

It creates its own backup, writes the row, and reopen-verifies. The recovery
runner now sets these env defaults itself (`env.setdefault(...)` in
`_launch_registration_worker`), so only older/other runners need the manual
env. Value is arbitrary but must match on both vars (conftest uses
`test-writer`).

The SAME two env vars gate the source workbook: CAPTCHA-confirmed Gmail
cleanup (`remove_captcha_dead_email_from_source()`) and the already-registered
mail removal fail with `BLOCKED_EXPECTED_WRITER_ID_MISSING:gmail_clean_v2`
when they are unset — the device account gets removed but the Excel row
survives. Always launch runners with the writer env set, not just the
tracking apply tool.

## Recovery runner flags: transport recovery is opt-in

`run_tiktok_recovery_new_handler.py` only runs `recover_android_transport`
(proxy-reassign + bounded soft reboot) when BOTH `--recover-after-failure`
AND `--full-scope-takeover` are passed. Defaults: `recover_after_failure=False`
and the runner hard-refuses `--recover-after-failure` without
`--full-scope-takeover` (~line 1069). A batch without these flags lets
`TIKTOK_STARTUP_NOT_FOREGROUND` / `PROFILE_TAB_FAILED` / `UI_XML_TIMEOUT`
final-block immediately even when transport recovery could save the machine.

Live proof (2026-08-05): STT 18 failed `TIKTOK_STARTUP_NOT_FOREGROUND` in the
no-flags batch; a re-run with `--stt 18 52 57 62 --max-workers 4
--recover-after-failure --full-scope-takeover` produced
`attempt_14_post_transport_recovery` → **VERIFIED_SUCCESS** (`@dieukieu03`,
wb=WRITTEN, row 107/Tik 141). The flags reclaim only dead-owner locks
(same project, or cross-project only when the user authorized it) — live
owners are never taken over.

## Re-running after a source-mail deletion: refresh the manifest first

Deleting a mail from `gmail_clean_v2.xlsx` (CAPTCHA-dead, already-registered,
mail-die) does NOT update the runner's manifest. The runner reads
`artifacts/pending/tiktok_reg_clean_targets.json` and injects the stale mail
via `SOCIAL_PREFERRED_EMAIL` → worker dies with
`Email override <stale> khong co trong Gmail source/Hotmail config cho STT N`.
Always re-run the detector (with `TIKTOK_REG_TARGETS_FILE` pointed at the
runner's manifest path) AFTER any source-row deletion, and inspect the
manifest before relaunching. A machine can also drop OUT of the manifest
entirely: if every remaining source mail for that STT already has a TikTok ID
in tracking (`registered_mailboxes`), the detector correctly stops selecting
it — check before assuming the machine is still runnable.

## Preflight before a live run

1. `adb devices` with `C:\Program Files (x86)\xiaowei\tools\adb.exe` — expect
   ~40 online.
2. Verify the pin: `python -c "import automation_core; print(importlib.metadata.version('automation-core'))"`
   must equal `REQUIRED_CORE_VERSION` in the runner, and the
   `recover_*` API must import (see the SKILL.md API-migration notes for the
   0.4.31-vs-0.4.35 break).
3. Confirm no live runner already owns the target locks
   (`process action=list`, lock files' PIDs).
