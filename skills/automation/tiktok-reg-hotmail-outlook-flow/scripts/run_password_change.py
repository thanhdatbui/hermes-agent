"""Change a TikTok password via the canonical tiktok-log-in module.

Verified 2026-08-16 (machine 57, row 453 derekbwpt78): password changed,
workbook updated with backup, account reopened with new password.

Usage (from git-bash):
  export TIKTOK_PASSWORD_WORKBOOK="D:\\OneDrive\\TaadaaData\\kibe\\taikhoan_dat_v2_updated .xlsx"
  export TIKTOK_F2A_PROVIDER_ROOT="D:\\Taadaa\\tiktok-add-bao-mat-f2a\\python_runner"
  export TIKTOK_REG_PROVIDER_ROOT="D:\\Taadaa\\Tiktok_Reg"
  python run_password_change.py --plan-only --rows 453     # review targets first
  python run_password_change.py --rows 453                 # live change

Notes:
- `--rows` targets exact workbook rows; `--machines` pulls EVERY account on the
  machine (including ones that already have a real password) — prefer --rows.
- The module has NO `__main__` block, so we call pc.main() explicitly.
- `--allow-live-password-change` is required for the real change (plan-only skips).
- The module does NOT screenshot success (journals stay empty) — verify by
  opening TikTok on the device (I18nSettingManageMyAccountActivity) or logging
  back in with the new password.
"""

import sys

sys.path.insert(0, r"D:\Taadaa\tiktok-log-in")

import login_runner.password_change as pc  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--allow-live-password-change" not in args and "--plan-only" not in args:
        print("Add --allow-live-password-change to perform the live change, "
              "or --plan-only to review targets first.")
        sys.exit(2)
    sys.exit(pc.main(args))
