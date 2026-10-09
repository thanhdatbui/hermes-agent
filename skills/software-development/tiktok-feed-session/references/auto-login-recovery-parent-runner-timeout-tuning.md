# Auto-Login Recovery Parent Runner Timeout Tuning & S7 AOD Stale XML Guard

## 1. Bối cảnh & Hiện tượng (2026-09-24)
- Trong các đợt chạy batch lướt feed nuôi tài khoản (`tiktok-luot nuoi acc`), khi runner mẹ phát hiện tài khoản chỉ định trong Excel bị thiếu trong Account Switcher, hàm `_maybe_recover_missing_account_via_login` trong `python_runner/flows/feed_swipe_smoke.py` tự động kích hoạt cơ chế login bù:
  1. `_run_fast_targeted_login`: Gọi `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <machine> --email <username> --ss --allow-parent-lock`.
  2. Fallback: Nếu fast login thất bại, gọi `D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py`.

## 2. Nguyên nhân Gốc rễ: Bị kill do Timeout trần của Runner Mẹ
- Trước ngày 2026-09-24, trong `feed_swipe_smoke.py` đặt giá trị default:
  - `fast_login_timeout_seconds = 180.0` (3 phút).
  - `reconcile_timeout_seconds = 300.0` (5 phút).
- Trên các thiết bị Samsung Galaxy S7 (CPU Exynos 8890, Android 7/8), chu trình mở TikTok, chuyển tab Profile, mở Switcher, bấm "Thêm tài khoản", nhập username/password, xử lý CAPTCHA hoặc OTP/2FA thường kéo dài từ 250s đến 380s.
- Khi chạm trần 180s, runner mẹ bắn SIGTERM kill `tiktok_login_v1.py` ngay lúc đang ở bước xác minh (`[auth] round 2/6`), sau đó fallback sang `reconcile_tiktok_accounts.py` cũng bị timeout 300s, dẫn đến phiên bị đánh dấu `manual-needed` oan uổng trong khi logic đăng nhập hoàn toàn đúng.

## 3. Bản vá Chuẩn hóa Timeout (2026-09-24)
File: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`
- Tăng `fast_login_timeout_seconds`: `180.0` $\rightarrow$ `420.0` (7 phút).
- Tăng `reconcile_timeout_seconds`: `300.0` $\rightarrow$ `600.0` (10 phút).
- Unit test đi kèm: `python_runner/tests/test_auto_login_fast_recovery.py` (`test_fast_login_default_timeout_increased`).

## 4. Cạm bẫy Stale XML /data/local/tmp & Màn hình AOD Samsung
- **Hiện tượng**: Agent kiểm tra thiết bị qua lệnh shell `uiautomator dump /data/local/tmp/uidump.xml` nhưng lại thấy các text lạ (ví dụ: popup Wi-Fi, hộp thoại cũ) không khớp với thực tế.
- **Nguyên nhân**:
  1. Thiết bị đang ở trạng thái Always-On-Display (`com.samsung.android.app.aodservice`) hoặc màn hình bị tối đen do dimmer.
  2. Lệnh `uiautomator dump` bị fail/kill ngầm hoặc không sinh file mới, khiến lệnh pull kéo lại file XML rác từ các phiên trước.
- **Kỷ luật điều phối & kiểm tra hiện trường**:
  1. Kiểm tra `dumpsys power` để biết màn hình có thực sự ON hay đang ngủ/AOD.
  2. Kiểm tra `dumpsys window windows | grep mCurrentFocus` để xác định chính xác Activity đang foreground.
  3. Bắt buộc đánh thức màn hình (`input keyevent 224` + `input keyevent 82`) trước khi thao tác.
  4. Sử dụng cổng `atx-agent` (port 7912) để dump UI XML tươi, cấm tuyệt đối tin vào file XML trong `/data/local/tmp` khi screencap không thể hiện điều đó.
