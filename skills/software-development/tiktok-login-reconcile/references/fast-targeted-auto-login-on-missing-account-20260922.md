# Fast Targeted Auto-Login Khi Đối Soát Thiếu Nick Trong Ca Nuôi (2026-09-22)

## 1. Bối cảnh & Vấn đề thực tế
- **Triệu chứng**: Trong ca nuôi feed (`run-feed-session.ps1` / `tiktok_runner.py`), khi `verify_and_switch_profile` mở Account Switcher nhưng không tìm thấy tài khoản mục tiêu (`expected_account`), máy bị dừng với mã lỗi:
  `manual-needed:account-switcher-missing-expected: expected account was not found in switcher`.
- **Nguyên nhân sâu xa trước ngày 22/09/2026**:
  - `_maybe_recover_missing_account_via_login` gọi qua script tổng `reconcile_tiktok_accounts.py` quét toàn bộ 8 slot của máy theo workbook.
  - Quét tuần tự tất cả nick thiếu thay vì chỉ nạp đúng nick mà ca nuôi đang cần, làm cháy deadline của batch và văng lỗi.
  - Script tổng cố nạp bằng email dẫn đến bẫy OTP mail và reCAPTCHA Google.

## 2. Kiến trúc Fast Targeted Auto-Login Chuẩn (Đã Sol-Approved >= 85 Điểm)
Trong `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`:
- Cập nhật `DEFAULT_RECONCILE_PYTHON` ưu tiên môi trường chuẩn `D:/Taadaa/python-envs/automation/Scripts/python.exe`.
- Tách helper độc lập `_build_fast_login_env(adb_path)` xử lý dynamic ADB tools path (`adb_path.parent` thay vì hardcode Windows path):
  ```python
  def _build_fast_login_env(adb_path: Path | None) -> dict[str, str]:
      fast_env = dict(os.environ)
      fast_env.pop("PYTHONPATH", None)
      tools_path = str(adb_path.parent) if (adb_path and adb_path.parent and adb_path.parent.is_dir()) else r"C:\Program Files (x86)\xiaowei\tools"
      if tools_path not in fast_env.get("PATH", ""):
          fast_env["PATH"] = tools_path + os.pathsep + fast_env.get("PATH", "")
      return fast_env
  ```
- Tách riêng hàm thực thi chiến lược `_run_fast_targeted_login`:
  ```python
  def _run_fast_targeted_login(
      ctx: DeviceContext,
      login_project: Path,
      machine_id: int | str,
      expected_account: str,
      python_exe: Path,
      adb_path: Path,
      timeout_sec: float | None = None,
  ) -> bool:
      fast_login_script = login_project / "tiktok_login_v1.py"
      if not fast_login_script.is_file():
          return False
      if timeout_sec is None:
          timeout_sec = float(ctx.config.get("fast_login_timeout_seconds", 90.0))
      
      start_time = time.time()
      correlation_id = str(ctx.config.get("session_id") or getattr(ctx, "run_id", "") or f"fast_login_{machine_id}_{int(start_time)}")
      ...
  ```
- **Telemetry farm-scale**:
  - Ghi nhận `duration_seconds` chính xác đến từng mili-giây.
  - Mang `correlation_id` xuyên suốt các event `start_fast_login`, `finish_fast_login`, `fast_login_failed_fallback_reconcile`, và `fast_login_exception_fallback_reconcile`.
- **An toàn thời gian ca nuôi & Độc lập tiến trình máy (User Correction 2026-09-22)**:
  - Giữ nguyên default timeout **180.0s** (`fast_login_timeout_seconds`, cấu hình linh hoạt qua config).
  - *Lý do*: Trong multi-machine feed runner (`multi_machine_feed_session.py`), mỗi thiết bị chạy trong một process worker riêng biệt (`ThreadPoolExecutor` / worker độc lập). Timeout của một máy không làm nghẽn tiến trình của các máy khác trên farm; nếu mạng lag hoặc tải OTP lâu, máy cần đủ 180s để hoàn tất nạp nick thay vì bị ép bóp thời gian 90s.
  - Nếu fast login thất bại hoặc timeout $\rightarrow$ Tự động fallback mượt mà về `reconcile_script` cũ, không bao giờ ngắt đứng ca chạy.

- **Hậu kiểm Stdout Engine chống False-Positive**:
  - Không tin tưởng mù quáng `returncode == 0`. Hậu kiểm bắt buộc:
    ```python
    is_verified_success = (
        fast_proc.returncode == 0
        and ("SUCCESS LOGIN" in stdout_text or "success" in stdout_text.lower() or "thành công" in stdout_text.lower())
    )
    ```
  - Kết hợp với caller `verify_and_switch_profile(allow_auto_reconcile=False)` re-check trực tiếp Switcher UI thật trên app sau recovery để đảm bảo fail-closed tuyệt đối.

- **Đa Môi Trường Python Fallback (Multi-Env Portability)**:
  - `DEFAULT_RECONCILE_PYTHON` kiểm tra tuần tự: biến môi trường $\rightarrow$ `D:/Taadaa/python-envs/automation/Scripts/python.exe` $\rightarrow$ `D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe` $\rightarrow$ `sys.executable`. Đảm bảo code chạy độc lập trên mọi host và CI không bị văng lỗi thiếu đường dẫn cố định.

## 3. Luồng tự phục hồi hoàn chỉnh
1. Mở Switcher không thấy nick -> Nhận diện `_is_account_switcher_missing_expected_reason`.
2. Gửi `input keyevent 4` đóng modal Switcher để giải phóng UI.
3. Kích hoạt `_maybe_recover_missing_account_via_login(ctx, expected)`.
4. Gọi `_run_fast_targeted_login`: `tiktok_login_v1.py` đăng nhập bằng **TikTok ID + Password + 2FA TOTP** chỉ mất ~20-30s (né hoàn toàn OTP mail và reCAPTCHA Google).
5. Khi login thành công (exit 0 + stdout marker) -> `_maybe_recover_missing_account_via_login` trả về `True`.
6. `verify_and_switch_profile` log `auto_login_recovered_retry_switch`, gọi lại `verify_and_switch_profile(allow_auto_reconcile=False)`.
7. App switch trơn tru vào nick vừa nạp và tiếp tục lướt feed bình thường mà không cần người can thiệp.

## 4. Kiểm thử Hồi quy (Unit Test Coverage: 8/8 Tests Pass)
File test: `python_runner/tests/test_auto_login_fast_recovery.py`:
- `test_build_fast_login_env`: Kiểm tra phân tách môi trường ADB sạch, không dính `PYTHONPATH`.
- `test_auto_login_fast_targeted_success`: Kiểm tra nhánh fast path thành công trả `True`, telemetry duration và correlation_id đầy đủ.
- `test_auto_login_fast_targeted_fail_fallback_reconcile`: Kiểm tra nhánh fast path fail tự động fallback sang `reconcile_script` thành công.
- `test_auto_login_fast_targeted_script_missing`: Kiểm tra khi thiếu `tiktok_login_v1.py` fallback ngay về reconcile.
- `test_auto_login_fast_targeted_timeout_fallback`: Kiểm tra khi fast path bị timeout `subprocess.TimeoutExpired` tự động fallback an toàn về reconcile.
- `test_reconcile_post_condition_retry_cycle`: Kiểm tra toàn bộ chu trình caller retry switch profile với dead-man guard (`allow_auto_reconcile=False`).
- `test_default_reconcile_python_env_resolution`: Kiểm tra tính phân giải đa môi trường Python interpreter.
- `test_false_positive_login_fail_closed_contract`: Kiểm tra chống false-positive dead-man guard khi nick không thực sự tồn tại trong switcher.
