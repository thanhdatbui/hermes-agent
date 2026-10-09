# Runner Mẹ Auto-Login Recovery Timeout & Telemetry Standard (2026-09-24)

## 1. Bối cảnh & Nguyên nhân sự cố
- Khi chạy feed session đa máy (`tiktok-luot nuoi acc`), nếu một máy phát hiện tài khoản bị thiếu trong Account Switcher (do TikTok tự động đăng xuất / evict nick), runner mẹ sẽ tự động gọi hàm cứu phiên:
  `_maybe_recover_missing_account_via_login` -> `_run_fast_targeted_login` -> thực thi `tiktok_login_v1.py <machine> --email <acc> --ss --allow-parent-lock`.
- Trên các dòng máy farm yếu như Samsung Galaxy S7 (SM-G930F/S/K):
  - Khởi động flow login từ app TikTok mất 15-30s.
  - Điền username/ID, chuyển trang mật khẩu, gõ mật khẩu mất 30-45s.
  - Vượt qua màn hình onboarding bàn phím Samsung, dismiss modals/camera mất 30-60s.
  - Chờ TikTok xác thực auth rounds (captcha kéo hình, 2FA prompt, kiểm tra thiết bị) mất 60-120s.
- Với timeout cũ `fast_login_timeout_seconds = 180.0` (3 phút), subprocess bị kill giữa chừng khi vừa mới submit password ở round 1-2. Khi timeout, runner mẹ fallback sang reconcile nhưng cũng bị nghẽn và đánh dấu máy `manual-needed`.

## 2. Chuẩn cấu hình Timeout trong Runner Mẹ
Trong file `python_runner/flows/feed_swipe_smoke.py`:
1. `_run_fast_targeted_login`:
   ```python
   timeout_sec = float(ctx.config.get("fast_login_timeout_seconds", 420.0))
   ```
   - Nâng default lên **420.0s (7 phút)**.
2. `_maybe_recover_missing_account_via_login` (Fallback Reconcile):
   ```python
   timeout_sec = float(ctx.config.get("reconcile_timeout_seconds", 600.0))
   ```
   - Nâng default lên **600.0s (10 phút)**.

## 3. Tiêu chuẩn Telemetry & Observability bắt buộc (Closeout Gate Invariant)
Khi sửa đổi hoặc mở rộng timeout trong runner, Reviewer (`closeout_gate.py`) yêu cầu ghi nhận đầy đủ telemetry để đo lường chi phí tài nguyên và thời gian chạy thực tế:
- **`start_fast_login` & `start_reconcile`**: Bắt buộc thêm `"timeout_seconds": timeout_sec` vào `extra`.
- **`finish_fast_login` & `finish_reconcile`**: Bắt buộc thêm `"duration_seconds": duration_seconds` và `"timeout_seconds": timeout_sec` vào `extra`.
- **`fast_login_failed_fallback_reconcile` / `fast_login_exception_fallback_reconcile`**: Bắt buộc ghi nhận `"duration_seconds"` và `"timeout_seconds"` để biết tiến trình đã chạy bao lâu trước khi fail/timeout.
- **Unit test**: Bắt buộc có test boundary override (ghi đè config qua `ctx.config`) và test exception timeout để đạt >= 85 điểm thẩm định Sol Auditor.

## 4. Cạm bẫy Stale XML Dump trên Android Device
- Khi inspect máy qua adb, file `/data/local/tmp/uidump.xml` có thể là bản dump của phiên trước hoặc của ứng dụng Settings Wi-Fi cũ.
- Tuyệt đối không kết luận máy bị dính popup Wi-Fi / kẹt màn hình chỉ từ 1 file dump XML nếu chưa đối chiếu với:
  1. `adb shell dumpsys window windows | grep -E "mCurrentFocus|mFocusedApp"`
  2. Ảnh chụp màn hình tươi qua `adb exec-out screencap -p`.
