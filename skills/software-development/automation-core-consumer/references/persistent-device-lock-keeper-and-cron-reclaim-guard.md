# Persistent Device Lock Keeper & Cron Reclaim Guard

Bài học xương máu từ sự cố ngày 06/10/2026: Coordinator nhận lệnh test app thủ công trên Máy 4, tự ghi file `machine_4.lock.json` bằng one-off script `python -c "...; os.getpid()..."`, sau đó gọi ADB thao tác CH Play. Đúng lúc này Cronjob Ca 3 thức dậy quét farm, thấy PID của lệnh `python -c` đã chết (`psutil.pid_exists == False`) nên hợp lệ coi là stale lock và ghi đè cướp máy, đẩy app nuôi acc lên che mất CH Play.

## 1. Gốc Rễ Lỗi Kỹ Thuật & Quy Trình
- **One-off Subprocess = Stale từ giây thứ 0:** Lệnh `python -c` chỉ chạy 0.1s rồi tắt. Ghi file lock với PID của một tiến trình đã chết là tự sát: mọi cơ chế dọn dẹp stale lock của farm (dựa trên PID liveness) sẽ dọn sạch file lock này và cấp quyền cho Cronjob khác.
- **Write-and-forget vs. Living Reservation:** Lock máy không phải là một hành động ném đá giấu tay (ghi file một lần rồi bỏ mặc). Lock máy là một **phiên giữ máy (reservation) gắn liền với vòng đời của một tiến trình còn sống thật sự**.

## 2. Công Cụ Chuẩn: `device_lock_keeper.py`
Vị trí: `D:/Taadaa/tools/device_lock_keeper.py` (đã được kiểm chứng 6/6 test suites và được Claude Advisor APPROVED).

### Cách sử dụng khi can thiệp thủ công / Canary / Probe:
```bash
# 1. Khởi động daemon nền giữ máy trước khi đụng vào ADB (mặc định max-duration 1800s):
python D:/Taadaa/tools/device_lock_keeper.py start --machine 4 --project "test_ad_hoc" --ttl 120

# 2. Kiểm tra trạng thái lock và nhịp tim sống:
python D:/Taadaa/tools/device_lock_keeper.py status --machine 4

# 3. Sau khi hoàn thành tác vụ, giải phóng máy an toàn:
python D:/Taadaa/tools/device_lock_keeper.py stop --machine 4

# 4. Hoặc chạy lệnh con trực tiếp bọc trong lease + heartbeat thread (tự giải phóng khi xong):
python D:/Taadaa/tools/device_lock_keeper.py run --machine 4 -- adb -s <serial> install app.apk
```

## 3. Kiến Trúc An Toàn Chốt Chặn (Approved bởi Claude Advisor)
1. **Living PID & Detached Daemon:** `start` spawn tiến trình con nền độc lập (`_worker`), duy trì PID sống thật sự (`psutil.pid_exists == True`) suốt phiên làm việc, triệt tiêu nguy cơ bị Cron dọn stale lock.
2. **Heartbeat & Dynamic `expires_at`:** Cứ mỗi 10s, daemon gọi `lease.heartbeat()` gia hạn `last_heartbeat` và `expires_at = now + ttl`.
3. **Hard Max-Duration Guard:** Giới hạn thời gian sống tối đa (mặc định 1800s = 30p). Nếu operator quên stop, daemon tự nhả lock tránh đóng băng máy vĩnh viễn.
4. **Graceful Stop via Sentinel File:** Khi gọi `stop`, script touch sentinel `machine_N.stop`. Daemon phát hiện và gọi `lease.release()` đầy đủ trước khi thoát, không phụ thuộc vào `taskkill /F`.
5. **Ownership Guard (Fail-Closed 100%):** Chỉ xóa file lock nếu `expected_lock_id == current_lock_id`. Nếu thiếu keeper file hoặc lock bị owner khác (Cron) chiếm -> TỪ CHỐI XÓA, in cảnh báo, bảo vệ tài nguyên người khác.
6. **Tri-State Process Status & Anti-Token Collision:**
   - Phân biệt rõ `True` (sống), `False` (chết), `None` (AccessDenied). Nếu `None` -> fail-closed ngay lập tức.
   - So khớp chính xác token `--machine N` trong argv, loại bỏ lỗi substring `--machine 4` trùng `--machine 42`.
