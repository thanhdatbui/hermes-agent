# Fast Targeted Auto-Login Khi Thiếu Nick Trong Ca Nuôi (2026-09-22)

## 1. Bối cảnh & Vấn đề
- **Triệu chứng**: Trong ca nuôi (`run-feed-session.ps1` / `tiktok_runner.py`), khi `verify_and_switch_profile` mở Account Switcher nhưng không tìm thấy tài khoản mục tiêu (`expected_account`), máy bị dừng với lỗi `manual-needed:account-switcher-missing-expected: expected account was not found in switcher`.
- **Nguyên nhân sâu xa trước đây**:
  - `_maybe_recover_missing_account_via_login` gọi `reconcile_tiktok_accounts.py` quét toàn bộ 8 slot của máy theo workbook.
  - Runtime cũ (`tiktok-reg-recovery`) dễ đụng lỗi import PIL hoặc timeout 300s/900s.
  - Quét tuần tự tất cả nick thiếu thay vì chỉ nạp đúng nick mà ca nuôi đang cần, làm cháy deadline của batch và văng lỗi `ACCOUNT_NOT_IN_SWITCHER`.

## 2. Giải pháp Fast Targeted Auto-Login (Đã triển khai - Commit `6b4e7d0`)
Trong `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`:
- Cập nhật `DEFAULT_RECONCILE_PYTHON` ưu tiên môi trường chuẩn `D:/Taadaa/python-envs/automation/Scripts/python.exe`.
- Trong `_maybe_recover_missing_account_via_login`, trước khi fallback sang `reconcile_script` nặng nề, bổ sung nhánh **Fast Targeted Login** gọi trực tiếp script chính thức `tiktok_login_v1.py`:
  ```python
  fast_login_script = login_project / "tiktok_login_v1.py"
  if fast_login_script.is_file():
      fast_env = dict(os.environ)
      fast_env.pop("PYTHONPATH", None)
      tools_path = r"C:\Program Files (x86)\xiaowei\tools"
      if tools_path not in fast_env.get("PATH", ""):
          fast_env["PATH"] = tools_path + os.pathsep + fast_env.get("PATH", "")
      fast_cmd = [
          str(python_exe),
          str(fast_login_script),
          str(machine_id),
          "--email", str(expected),
          "--ss",
      ]
      fast_proc = subprocess.run(fast_cmd, capture_output=True, text=True, env=fast_env, timeout=180.0)
      if fast_proc.returncode == 0:
          return True
  ```

## 3. Luồng tự phục hồi hoàn chỉnh
1. Mở Switcher không thấy nick -> Nhận diện `_is_account_switcher_missing_expected_reason`.
2. Gửi keyevent 4 đóng modal Switcher để giải phóng UI.
3. Kích hoạt `_maybe_recover_missing_account_via_login(ctx, expected)`.
4. `tiktok_login_v1.py` đăng nhập bằng **TikTok ID + Password + 2FA TOTP** chỉ mất ~20-30s (né hoàn toàn OTP mail và reCAPTCHA Google).
5. Khi login thành công (exit 0) -> `_maybe_recover_missing_account_via_login` trả về `True`.
6. `verify_and_switch_profile` log `auto_login_recovered_retry_switch`, gọi lại `verify_and_switch_profile(allow_auto_reconcile=False)`.
7. App switch trơn tru vào nick vừa nạp và tiếp tục lướt feed bình thường mà không cần người can thiệp.
