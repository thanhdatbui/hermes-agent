# Bẫy Timeout 180s Auto-Login Recovery trong Feed Session & Hợp Đồng Worker Login

## 1. Hiện Tượng (Root Cause 24/09/2026)
Trong các phiên nuôi/lướt feed (`tiktok-luot nuoi acc`), khi runner phát hiện thiếu tài khoản mục tiêu trong Switcher (do tài khoản bị văng/evict hoặc chưa login), runner kích hoạt cơ chế tự cứu phiên:
`feed_swipe_smoke.py` -> `_run_fast_targeted_login()` -> gọi `tiktok_login_v1.py <STT> --email <ID> --ss --allow-parent-lock`.

Tuy nhiên, `_run_fast_targeted_login()` áp dụng timeout cứng:
```python
timeout_sec = float(ctx.config.get("fast_login_timeout_seconds", 180.0))
```
Trên các thiết bị S7/Android 7 cũ:
- Quá trình mở TikTok, vào hồ sơ, mở switcher, bấm Thêm tài khoản, gõ ID, chuyển sang màn hình password, gõ password và chờ server TikTok xử lý auth/challenge (round 1 -> round 2) thường mất từ 150s - 220s.
- Tại mốc 180s, tiến trình `tiktok_login_v1.py` bị `subprocess.TimeoutExpired` giết ngang khi đang ở giữa bước xác minh auth!
- Runner mẹ hiểu nhầm là login thất bại, fallback sang `reconcile_tiktok_accounts.py` (cũng timeout 300s) rồi dừng phiên và đánh dấu `manual-needed:account-switcher-missing-expected`.
- Hệ quả: User nhìn vào báo cáo thấy văng tài khoản và tưởng hệ thống không chịu gọi hàm login lại, trong khi thực tế hàm login đã chạy nhưng bị bóp chết giữa chừng.

## 2. Quy Tắc Xử Lý Cứu Phiên Cho Coordinator
1. **Kiểm tra log `auto_login_recovery`**:
   Trước khi báo cáo tài khoản văng và cần can thiệp thủ công, Coordinator BẮT BUỘC kiểm tra `log.jsonl` xem có event `auto_login_recovery` bị timeout hay không:
   ```bash
   grep -E "auto_login_recovery|fast_login" <path_to_log.jsonl>
   ```
2. **Dispatch Worker Login Độc Lập Phải Đặt Timeout ≥ 360s**:
   Khi Coordinator dispatch worker subagent để login bù bằng `tiktok_login_v1.py`, worker KHÔNG bị ràng buộc bởi lock của feed session (nếu feed session đã kết thúc) nhưng BẮT BUỘC phải đặt `timeout=360` trong terminal call.

## 3. Hợp Đồng Đóng Gói Lệnh (One-Touch Execution Contract) Cho Worker Login
Để tránh bẫy Worker bị timeout 600s do lãng phí iterations vào việc tìm kiếm môi trường (`which adb`, đọc file mã nguồn, gọi skill_view), Coordinator BẮT BUỘC đóng gói sẵn toàn bộ môi trường trong prompt dispatch:
- **Cung cấp sẵn PATH chứa ADB**:
  `export PATH="/c/Program Files (x86)/xiaowei/tools:$PATH"`
- **Cung cấp Python Venv chuẩn**:
  `"D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe"`
- **Lệnh 1 chạm chuẩn**:
  ```bash
  cd /d/Taadaa/Tiktok_Reg && export PATH="/c/Program Files (x86)/xiaowei/tools:$PATH" && env -u PYTHONPATH "D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" tiktok_login_v1.py <STT> --email <ID> --ss
  ```
- **Nghiệm thu bắt buộc trước teardown**:
  Chụp ảnh Account Switcher (`exec-out screencap -p > /d/Taadaa/reports/...png`) để chứng minh tài khoản đã hiện diện và active, kèm dòng `MEDIA:<path_anh>`.

## 4. Chống Bẫy Báo Cáo Phantom Popup Do Stale XML Dump
Khi dùng `adb shell uiautomator dump /data/local/tmp/uidump.xml`:
- Nếu `uiautomator dump` bị fail âm thầm (hoặc crash), file `uidump.xml` cũ của ca trước vẫn nằm trong `/data/local/tmp`. Khi pull về máy tính, Coordinator sẽ đọc nhầm nội dung của ca cũ (ví dụ popup Wi-Fi, popup cập nhật) và báo cáo sai hiện trường cho User.
- **Biện pháp bắt buộc**:
  1. Luôn `adb shell rm -f /data/local/tmp/uidump.xml` trước khi dump mới.
  2. Đối soát bắt buộc với `screencap` thực tế và `dumpsys window windows | grep -E "mCurrentFocus|mFocusedApp"`.
  3. CẤM khẳng định máy bị kẹt popup nếu chưa nhìn thấy popup đó trên ảnh screencap thực tế.
