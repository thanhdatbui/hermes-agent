# Hotmail Security Automation via GPM Playwright CDP

Script: `D:\Taadaa\Hotmail\scripts\gpm_change_hotmail_security.py`
Unit Tests: `D:\Taadaa\Hotmail\tests\test_gpm_change_hotmail_security.py`

## CLI Parameters
- `--machine <int>`: Số máy farm (e.g. 2, 40)
- `--email <str>`: Chỉ định email Hotmail cụ thể
- `--canary`: Chế độ canary (chỉ chạy đúng 1 account đại diện để kiểm chứng)
- `--live`: Bắt buộc để thực sự click submit đổi pass và ghi Excel
- `--max-targets <int>`: Số lượng tài khoản tối đa mỗi lượt (mặc định 1)

## Architecture & GPM Profile Mapping
1. **GPM Profile Lookup**:
   - Queries GPM Local API `v3` (`http://127.0.0.1:19995/api/v3/profiles`).
   - Match pattern: `f"{machine:02d} - "`, `f"{machine} - "`, `f"M{machine:02d} - "`.
   - Group Priority: `group_id=1` or `group_id=10`.
2. **CDP Connection**:
   - Starts profile via `client.start_profile(profile_id)`.
   - Connects via Playwright: `sync_playwright().chromium.connect_over_cdp(f"http://{addr}")`.

## Security Flow Steps & Checkpoints
1. **Login (`https://login.live.com`)**:
   - Fill `#i0116` (email) -> click `#idSIButton9`.
   - Fill `#i0118` (current password) -> click `#idSIButton9`.
   - Handle KMSI prompt ("Duy trì đăng nhập?") -> click `#idBtn_Back` ("Không").
   - Screenshot Checkpoint 1: `D:\Taadaa\runtime\artifacts\gpm_login_{safe_email}.png`.
2. **Password Change (`https://account.live.com/password/change`)**:
   - Fill `#currentPassword`.
   - Generate strong 14-char password (`gen_strong_password(14)`).
   - Fill `#newPassword` and `#confirmPassword`.
   - Screenshot Checkpoint 2: `D:\Taadaa\runtime\artifacts\gpm_pre_change_{safe_email}.png`.
   - If `--live`: Submit `#save` / `#idSubmit_SAV_btnSubmit` and wait.
   - Screenshot Checkpoint 3: `D:\Taadaa\runtime\artifacts\gpm_post_change_{safe_email}.png`.
3. **Sign Out Everywhere (`https://account.live.com/proofs/manage/additional`)**:
   - Locate and click "Sign out everywhere" / "Đăng xuất khỏi mọi nơi".
   - Confirm popup if prompted.
   - Screenshot Checkpoint 4: `D:\Taadaa\runtime\artifacts\gpm_signout_{safe_email}.png`.
4. **Excel & State Sync**:
   - When `--live`, updates Column G (PASS MAIL) in `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`.
   - Updates state tracking in `D:\Taadaa\runtime\kibe\cron-state\hotmail_changed_tracker.json`.
5. **Teardown**:
   - Closes page and calls `client.stop_profile(profile_id)`.
   - Emits stdout checkpoints with `MEDIA:` tag for verification gate compatibility.
