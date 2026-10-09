# Device Lock Hard Enforcement & Anti-Tampering Rules

## 1. Nguyên Tắc Cốt Tử: Cấm Can Thiệp Bằng Ý Chí / Cấm Hứa Suông
- Cơ chế bảo vệ Farm KHÔNG BAO GIỜ được dựa vào "trí nhớ" hay "sự tự giác" của LLM/Coordinator.
- Mọi chốt chặn an toàn BẮT BUỘC phải là **HARD CODE ENFORCEMENT** (chặn cứng ở cấp code, fail-closed).

## 2. Hard Lock Enforcement trong Code
1. **Tuyệt đối cấm cờ Opt-in bypass lock:**
   - CẤM các biến môi trường dạng `DEVICE_LOCK_ENABLED = os.environ.get(...)` mà mặc định là `False`.
   - Mọi script tác vụ (như `social_reg_v1.py`) khi khởi chạy bắt buộc phải ép cứng `user_authorized=True`, đăng ký file lock chuẩn `machine_<N>.lock.json` vào `~/.codex/device-locks/`.
2. **Khóa cứng ngay tại Entrypoint:**
   - Trước khi script gửi bất kỳ lệnh can thiệp nào (kể cả mở app hay gõ phím), BẮT BUỘC phải gọi `_acquire_social_device_lock_or_skip()`.
   - Nếu máy đang có file lock bởi tiến trình khác (PID alive) -> **LẬP TỨC ABORT / SAFE-SKIP**, không được tiếp tục.
3. **Bảo đảm thu hồi trong `finally:`**:
   - `dev_lease.release()` phải nằm trong khối `finally:` để không bao giờ bị rò rỉ lock khi xảy ra ngoại lệ.
4. **Structured Telemetry bắt buộc:**
   - Ghi log chuẩn hóa:
     * `[telemetry:device-lock] machine={stt} serial={device_id} action=acquire_conflict status=safe_abort reason=active_lock_by_other_process`
     * `[telemetry:device-lock] machine={stt} serial={device_id} action=acquired status=active lease_id=...`
     * `[telemetry:device-lock] machine={stt} serial={device_id} action=released status=closed`

## 3. Quyền Force-Stop & Teardown
- Lệnh ADB `am force-stop` và `input keyevent 3` (HOME) là cần thiết khi test đồ/hygiene, NHƯNG **CHỈ ĐƯỢC PHÉP THỰC THI BỞI CHÍNH TIẾN TRÌNH ĐANG GIỮ LOCK CỦA MÁY ĐÓ**.
- CẤM TUYỆT ĐỐI Coordinator hoặc tiến trình ngoài lề nhảy vào `force-stop` hoặc bấm `HOME` trên một máy mà PID khác đang nắm lock (ví dụ: máy đang chạy add 2FA hoặc feed session).
- Khi gặp màn hình lạ: Thực hiện `Doubt -> Freeze -> Report -> Wait`, cấm tự quy kết là "máy kẹt/treo" rồi tự tay dọn dẹp phá tiến trình của người khác.

## 4. Cơ Chế Reaper Thu Hồi Lock Treo (>1h TTL)
- Script watchdog `D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py` tự động chạy định kỳ:
  * Lock quá 1 giờ (TTL 3600s) HOẶC tiến trình sở hữu đã chết (`owner_dead`) -> Tự động chuyển lock vào vùng cách ly (`.codex/device-locks-reaped/`) và chạy ADB cleanup về HOME an toàn.
  * Nếu PID sở hữu còn sống và chưa quá TTL 1h -> BẮT BUỘC GIỮ NGUYÊN LOCK, cấm mọi hành vi bẻ/xóa lock.
