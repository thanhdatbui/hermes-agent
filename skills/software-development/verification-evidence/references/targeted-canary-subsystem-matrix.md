# Targeted Canary Subsystem Matrix & Gate Guard Architecture

## 1. Problem Statement: "Canary Máy Móc"
Agents frequently fall into the trap of running a generic canned test (e.g., swiping 3 videos on TikTok feed or checking that `exit_code == 0` without a Home screen) to claim "Canary Passed", regardless of what was actually modified in `git diff`.
- A fix in `account_switcher` proved by a video feed swipe is **UNVERIFIED**.
- A fix in `2fa_login` proved by opening Profile without auth verification is **UNVERIFIED**.
- A fix in `avatar_upload` proved without profile pHash / crop verification is **UNVERIFIED**.

## 2. Subsystem Mapping & Required Evidence Matrix

| Subsystem in Git Diff | Candidate Paths / Modules | Mandatory Canary Command / Hook | Mandatory WinRT OCR Keywords (Whitelist) |
|---|---|---|---|
| `account_switcher` | `core/account_switcher.py`, `flows/feed_swipe_smoke.py` (`*_switch*`) | `run_tiktok.py` with `--account-workbook` & `--account-row-index` (or `--hook account_switcher`) | `Chuyển tài khoản`, `Thêm tài khoản`, `Switch account`, `Add account` |
| `profile_identity` | `flows/profile_flow.py`, `_profile_identity*` | `--mode feed-session-smoke --verify-profile` | `Hồ sơ`, `Sửa hồ sơ`, `Edit profile`, exact `@username` target |
| `feed_swipe` | `flows/swipe_flow.py`, `feed_swipe_smoke.py` (`*_swipe*`) | `--mode feed-swipe-smoke` | `Dành cho bạn`, `Đang follow`, `Bạn bè`, `For You` |
| `2fa_security` | `tiktok-add-bao-mat-f2a`, `flows/twofa*` | `--mode 2fa-verify` / auth verification flow | `Xác minh 2 bước`, `2-step verification`, `Trình xác thực`, `Mã xác thực` |
| `follow_target` | `follow_runner/run_follow.py` | `follow_runner` with `--hook follow_target` | `Đang follow`, `Following`, `Bạn bè`, `Friends` |
| `avatar_upload` | `avatar*`, `upload_preflight*` | `--mode avatar-upload-smoke` | Profile screen + pHash/BGR delta > 15 against baseline |

## 3. Automated Subsystem Extraction from Git Diff
Before accepting a canary receipt, the verification gate (`canary_runner.py` or `done_gate.py`) must:
1. Inspect `git diff --name-only HEAD~1..HEAD` (or current worktree diff).
2. Classify the modified functions/files into one or more `required_subsystems`.
3. Compare against `canary_receipt.json`:
   - `subsystem_tested`: Must match the diff's `required_subsystems`.
   - `ocr_snippet` / `media_path`: Must pass `validate_evidence_screen.py <media_path> <subsystem>`.
4. If a mismatch is detected (e.g., diff touched `account_switcher` but receipt recorded `feed_swipe`), gate fails with:
   `[CANARY_FAIL] CANARY_SUBSYSTEM_MISMATCH: Diff requires 'account_switcher', but canary only tested 'feed_swipe'!`

## 4. O(1) Fast-Canary Rule
Targeted canaries do NOT need to run full 5-minute sessions. They should execute the minimal focused hook (O(1) execution <= 30s):
- Open target screen / trigger dialog.
- Capture screenshot & dump XML.
- Validate via WinRT OCR.
- Teardown only AFTER capture is confirmed.
