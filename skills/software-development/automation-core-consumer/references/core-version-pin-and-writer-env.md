# Core version pin, writer-identity env, and recovery-runner lessons (2026-08-05)

Session: Tiktok_Reg recovery run for 15 machines (STT 16,18,30,31,34,36,38,39,
40,52,54,55,57,62,66). Two registrations verified+written (`@chuanh0400` row
93/122, `@dieukieu03` row 107/141); three dead/captcha mails removed from Excel
+ device; a new core module `outlook_health` added.

## 1. The phantom version pin

`scripts/run_tiktok_recovery_new_handler.py` pinned `REQUIRED_CORE_VERSION =
"0.4.30"`. That version never existed. Real bump history:

```
git log -p --all -- pyproject.toml | grep -E "^\+version"
0.4.19 ... 0.4.20 0.4.21 0.4.22 0.4.23  →  0.4.28 (baseline, 6579419)
→ 0.4.31 (64f0206, transactional lock, keeps old recovery API)
→ 0.4.35 (HEAD, reconcile transactional recovery core)
```

- 0.4.28 and 0.4.31 both export `recover_android_transport` /
  `recover_missing_android_vpn` / `MissingVpnRecoveryError`.
- HEAD (0.4.35/0.4.36) deletes those and replaces them with
  `soft_reboot_and_wait` / `reboot_and_restore` — old runners die on import.
- Fix: pin the **last API-compatible commit**, build from a `git archive` of
  that commit (not `git checkout <sha> -- pyproject.toml`, which only restores
  the version line while `src/` stays at HEAD):
  ```bash
  rm -rf /d/Taadaa/_core031_build && mkdir -p /d/Taadaa/_core031_build
  git archive 64f0206 | tar -x -C /d/Taadaa/_core031_build
  cd /d/Taadaa/_core031_build && python -m build --wheel
  pip install --force-reinstall --no-deps dist/automation_core-0.4.31-*.whl
  ```

## 2. Editable-install overwrite hazard

Running `pip install -e .` in automation-core (to test a new module) rewires
the shared Python env to the source tree. The consumer runner then imports the
source HEAD API instead of the pinned 0.4.31:

```
ImportError: cannot import name 'AndroidTransportRecoveryError'
from 'automation_core.device_recovery' (D:\Taadaa\automation-core\src\...)
```

- Rule: **test core with `PYTHONPATH=D:\Taadaa\automation-core\src`, never
  editable install into the runner env.** Reinstall the pinned wheel after any
  core test session.
- Verify the running env actually has the pinned version:
  ```python
  import automation_core, importlib.metadata as m
  print(m.version('automation-core'), automation_core.__file__)
  # want 0.4.31 + site-packages, NOT ...\automation-core\src
  ```

## 3. Writer-identity env contract

`workbook_transaction_adapter.transactional_workbook_update()` reads
`TIKTOK_REG_EXPECTED_WRITER_ID` / `TIKTOK_REG_WRITER_ID` from env and passes
them to `single_writer_workbook_update` → `assert_writer_identity`. Both empty
→ `BLOCKED_EXPECTED_WRITER_ID_MISSING:<logical_id>`; declared != expected →
`BLOCKED_WRONG_WRITER_ID`.

Every runner that (a) spawns `social_reg_v1.py --defer-tracking-write` workers
or (b) applies deferred results must set both env vars to the same
machine-local value. Patch the runner's `_launch_registration_worker`:

```python
env = os.environ.copy()
env.setdefault("TIKTOK_REG_WRITER_ID", "tiktok-reg-runner")
env.setdefault("TIKTOK_REG_EXPECTED_WRITER_ID", "tiktok-reg-runner")
```

Failure symptoms seen live:
- STT 16: reg succeeded (profile proof XML/PNG + `tracking_result_*.json`) but
  `write_deferred_results_sequential` failed with
  `BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking`. Fixed by re-running
  `scripts/apply_deferred_tracking_results.py` with the two env vars set →
  `WRITTEN`, reopen-verify passed.
- STT 40: CAPTCHA cleanup removed the device account (`ALREADY_ABSENT`) but
  `remove_captcha_dead_email_from_source` failed with
  `BLOCKED_EXPECTED_WRITER_ID_MISSING:gmail_clean_v2` — the Excel row
  survived. After the env fix, the same flow deleted the row
  (`DELETED_AND_VERIFIED` with backup).

## 4. Recovery-runner gating

- `--recover-after-failure` defaults off, and `run()` raises unless
  `--full-scope-takeover` is also passed.
- `recover_android_transport` evidence: `{"method": "proxy_reassign",
  "rebooted": false, ...}` — it reassigns the proxy and recaptures, it does
  NOT reboot when transport recovers.
- When the recapture succeeds but TikTok still crashes back to the launcher
  (`mCurrentFocus=...com.sec.android.app.launcher...`), transport recovery is
  not enough: `adb reboot` + wait `sys.boot_completed=1` + settle, then retry.
- Post-reboot the VPN may not be back: `ip addr show tun0` returns nothing →
  `VPN_RECOVERY_FAILED: proxy readiness timed out`. That is a proxy-watcher /
  device state issue, not a code failure.

## 5. Detector manifest staleness

`_detect_clean.py` writes the target manifest to
`artifacts/pending/tiktok_reg_clean_targets.json` (under `.runtime/`). The
recovery runner reads exactly that file. After deleting a source mail,
re-run the detector, or the runner still uses `SOCIAL_PREFERRED_EMAIL` of the
deleted mail → `[07] Email override ... khong co trong Gmail source` final
block.

Email that reaches the TikTok "đã có tài khoản" login path but has no ID in
the tracking workbook was created outside this pipeline (or reused). It is
NOT a registration target — remove it from `gmail_clean_v2.xlsx` (backup +
reopen-verify) so the detector stops selecting it.

## 6. Vietnamese header aliases

`gmail_clean_v2.xlsx` `Gmail Accounts` sheet headers:
`số máy | tài khoản gmail | pass mail | ...`.

- Add `tai khoan gmail` and `tai khoan` to the `email` alias frozenset in
  `scripts/tiktok_target_eligibility.py`.
- Do NOT put bare `tik` in the `tiktok_id` alias set: the tracking sheet
  `Tài Khoản` has `Tik` (slot) and `ID` (username) → ambiguous header error
  `TRACKING_WORKBOOK_HEADERS_AMBIGUOUS: tiktok_id`.

## 7. Health-check parity: Gmail done, Hotmail added in core

- Gmail: after OTP exhaustion `handle_tiktok_email_otp` calls
  `check_google_account_health_from_gmail` → `run_google_live_check` →
  `HEALTH_CAPTCHA` → `cleanup_captcha_account` (device-first, then Excel).
- Hotmail had no equivalent → dead mail never removed.
- New core module `automation_core/outlook_health.py` (bump 0.4.36):
  - `OutlookHealthCallbacks(open_inbox, read_ui, classify_ui, continue_sign_in,
    wait_after_action)` — thin UI adapters, core owns sequencing.
  - `run_outlook_health_check(...)` state machine with
    `max_steps=20, max_state_repeats=3`, returns `OutlookHealthResult(status,
    reason, xml)`; statuses `HEALTH_NORMAL` / `HEALTH_RELOGIN` /
    `HEALTH_LOCKED` / `HEALTH_MANUAL` / `HEALTH_UNKNOWN`.
  - Classifiers match the **whole XML blob** (labels live in attributes), strip
    Vietnamese accents via NFKD **and** `đ→d` (NFKD alone keeps `đ`, so
    `đã bị khóa` does not match `da bi khoa`).
  - Consumer rule: only remove mail on `HEALTH_RELOGIN`/`HEALTH_LOCKED`; never
    on `HEALTH_NORMAL`. Verify deletion through
    `remove_captcha_dead_email_from_source` (backup + reopen-verify).
  - Tests: `tests/test_outlook_health.py` (7 tests); core suite 443 passed.
