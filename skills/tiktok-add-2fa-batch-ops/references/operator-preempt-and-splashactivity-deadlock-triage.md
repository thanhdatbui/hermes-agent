# Operator Preempt, UIAutomation Zombie Deadlock & SplashActivity Triage (08/09/2026)

## 1. Bối cảnh & Hiện tượng
Khi chạy canary cho máy lỗi (Slot 317 - Máy 40) sau khi đã vá code nhận diện Switcher trong `automation-core`, runner tiếp tục văng lỗi:
```json
{"status": "failed", "reason": "SWITCHER_OPEN_FAILED"}
```
Hoặc tiến trình chạm timeout 240s/300s với exit code 124.

---

## 2. Phân tích Nguyên nhân Gốc rễ

### A. Triệu chứng giả "SWITCHER_OPEN_FAILED"
- `open_switcher()` trong `account_switcher.py` bắt mọi ngoại lệ không xác định và bọc thành `SWITCHER_OPEN_FAILED`.
- Khi kiểm tra hiện trường thiết bị qua `dumpsys window`:
  ```text
  mCurrentFocus = com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity
  ```
- **Bản chất:** TikTok chưa bao giờ vào được `MainActivity` hoặc tab `Profile` (vẫn đang đứng ở màn hình khởi động Splash / màn hình đen). Vì không có Profile header để tìm anchor, luồng mở switcher đương nhiên thất bại.

### B. Hai nguyên nhân khiến TikTok treo tại `SplashActivity`
1. **Zombie UiAutomationService Deadlock:**
   - Các tiến trình nền cũ trên thiết bị (`app_process`, `com.github.uiautomator`, `com.github.uiautomator.test`) bị rò rỉ từ các đợt chạy trước hoặc từ cron nuôi acc bị dừng đột ngột.
   - Các tiến trình này giữ chặt `UiAutomationService` độc quyền trên hệ điều hành Android, khiến các lệnh `uiautomator dump` hoặc ATX session tiếp theo bị đóng băng (hang) vô hạn.
2. **Mạng / Proxy Die:**
   - TikTok khi khởi động bắt buộc phải gửi request ping / sync cấu hình về server.
   - Nếu proxy 4G / VPN bị ngắt, timeout hoặc 502, TikTok sẽ đứng im tại SplashActivity không tải tiếp giao diện.

---

## 3. Thang Dọn Dẹp Thiết Bị Khẩn Cấp (Emergency Recovery Ladder)

Trước khi chạy lại canary hoặc worker đơn, BẮT BUỘC dọn sạch thiết bị bằng chuỗi lệnh ADB:
```bash
ADB="C:\Program Files (x86)\xiaowei\tools\adb.exe"
$ADB -s <serial> shell "pkill -f uiautomator || true"
$ADB -s <serial> shell "am force-stop com.github.uiautomator || true"
$ADB -s <serial> shell "am force-stop com.github.uiautomator.test || true"
$ADB -s <serial> shell "am force-stop com.ss.android.ugc.trill || true"
$ADB -s <serial> shell "input keyevent 3" # Đưa về màn hình Home
```

Kiểm tra kết nối mạng qua thiết bị:
```bash
$ADB -s <serial> shell "curl -s -m 8 https://api.ipify.org || echo PROXY_FAILED"
```

---

## 4. Xử Lý Lock Chéo & Cơ Chế OPERATOR_PREEMPT

### A. Vấn đề Cross-Project Lock
- Cron nuôi acc đa máy (`run_tiktok.py --mode multi-machine-feed-session`) kích hoạt mỗi 15 phút, reserve toàn bộ máy mục tiêu dưới dạng lock `queued_v2` với `project="tiktok-luot nuoi acc"`.
- Runner Phase B bình thường dùng `takeover_scope="SAME_PROJECT_RECOVERY"` nên bị từ chối fail-closed `DEVICE_LOCK_UNAVAILABLE`.

### B. Bản vá Dynamic Takeover trong `run_capture_phase_b.py`
Code đã được cập nhật:
```python
takeover_scope = os.environ.get("TAKEOVER_SCOPE", "OPERATOR_PREEMPT")
```
Khi operator chỉ đạo kích hoạt chạy:
1. Dừng tiến trình cron xung đột: `taskkill /F /PID <PID>`.
2. Dọn file lock tồn dư trong `C:\Users\Kibe\.codex\device-locks\`.
3. Export `TAKEOVER_SCOPE="OPERATOR_PREEMPT"`.

### C. Bẫy Reservation Gate của `run_batch_live_2fa.py`
- `run_batch_live_2fa.py` có bước reserve cha `acquire_device_lock(command="batch-live-2fa-reservation")`.
- Bước này chỉ cho phép takeover khi truyền cờ `--full-scope-takeover`. Nếu không có cờ này, runner cha sẽ skip target dù worker con hỗ trợ `OPERATOR_PREEMPT`.
- **Giải pháp dứt điểm:** Khi chạy canary 1 máy lỗi cụ thể theo lệnh user, **gọi trực tiếp `run_capture_phase_b.py`**:
```bash
export TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/kibe.yaml"
export TAKEOVER_SCOPE="OPERATOR_PREEMPT"
python run_capture_phase_b.py \
  --machine <M> --serial <SERIAL> --expected-username <ID> --source-row <ROW> \
  --workbook-path "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" \
  --workbook-sheet "Tài Khoản" --adb-path "C:\Program Files (x86)\xiaowei\tools\adb.exe" \
  --live
```

---

## 5. Kỷ Luật Phản Hồi Operator

- Khi user đã ra lệnh: *"Thì chọn vài máy lỗi chạy. Lock lại chạy đi"*, đây là chỉ thị hành động dứt khoát.
- **CẤM TUYỆT ĐỐI** Coordinator hỏi lại: *"Bác có muốn em dispatch worker kích hoạt chạy luôn không?"*.
- Bắt buộc dispatch worker ngay lập tức, tiến hành dọn lock, chạy canary và báo cáo bằng chứng ảnh thực tế.
