# Kỷ Luật Khóa 2 Chiều (Two-Way Device Lock), Chống Phá Hoại & Cơ Chế Reaper (21/09/2026)

## 1. Bản chất sự cố Coordinator phá hoại (Root Cause Incident)
- **Hiện tượng:** Coordinator thấy Máy 42 đang dừng ở màn hình *"Thiết lập xác minh 2 bước"* (Authenticator App), lập tức quy chụp là máy bị kẹt và tự ý chạy:
  ```bash
  adb -s ce06160692e07d0404 shell am force-stop com.ss.android.ugc.trill
  adb -s ce06160692e07d0404 shell input keyevent 3
  ```
- **Hậu quả nghiêm trọng:** Máy 42 thực tế đang được điều khiển bởi tiến trình script Add 2FA (`run_batch_live_2fa.py` / `tiktok-add-bao-mat-f2a`). Hành vi tự ý force-stop và Home của Coordinator đã phá hủy trực tiếp tiến trình bảo mật đang chạy của hệ thống.
- **Nguyên nhân cốt tử:**
  1. *Tunnel Vision & Mất Situational Awareness:* Chỉ chăm chăm vào task test của mình, không quan tâm hệ thống đang có flow khác chạy song song.
  2. *Quy chụp sai:* Thấy màn hình không thuộc flow của mình liền coi là "lỗi" và tự ý "dọn dẹp".
  3. *Lỗ hổng Bypass Lock trong `social_reg_v1.py`:* Script có cờ `DEVICE_LOCK_ENABLED` opt-in qua biến môi trường. Khi chạy CLI đơn lẻ không truyền cờ, script bỏ qua hoàn toàn việc tạo file lock `machine_<N>.lock.json`, khiến hệ thống không biết máy đang chạy gì.

---

## 2. Invariant Bất Khả Xâm Phạm (Anti-Sabotage Invariants)

### Rule 1: Tuyệt đối CẤM can thiệp máy khi chưa sở hữu Lock (Hands-Off Rule)
- Trước khi thực hiện bất kỳ lệnh ADB mang tính thay đổi trạng thái (`am force-stop`, `input tap`, `input keyevent`, `input text`, `am start`):
  - BẮT BUỘC kiểm tra active lock: `~/.codex/device-locks/machine_<N>.lock.json`.
  - Nếu file lock tồn tại và PID chủ sở hữu còn sống (`psutil.pid_exists(pid)` / `owner_process_alive()`):
    👉 **TUYỆT ĐỐI KHÔNG ĐƯỢC CHẠM VÀO MÁY (HANDS OFF 100%)**.
  - Dù trên màn hình là gì (Authenticator, QR code, Profile, hay Settings), CẤM tự ý force-stop hay bấm Home.

### Rule 2: Quyền hạn của lệnh `am force-stop` khi test đồ
- Lệnh `am force-stop` là thao tác dọn dẹp vệ sinh môi trường (hygiene) cần thiết trước và sau khi test để app về trạng thái sạch (clean state).
- **ĐIỀU KIỆN TIÊN QUYẾT:** Lệnh này **CHỈ ĐƯỢC PHÉP THỰC THI BỞI CHÍNH TIẾN TRÌNH ĐANG SỞ HỮU DEVICE LOCK TRÊN MÁY ĐÓ**.
- Tiến trình ngoài cuộc hoặc Coordinator tuyệt đối không được gọi `force-stop` thay cho máy của tiến trình khác.

### Rule 3: Cơ chế Reaper Cron tự động tháo lock sau 1h (`reap-dead-owner-locks.py`)
- Hệ thống farm ĐÃ CÓ SẴN cơ chế tự động dọn dẹp an toàn:
  - Script: `D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py`.
  - TTL: **3600 giây (1 giờ)**.
  - Quét thư mục `~/.codex/device-locks/`.
  - Nếu phát hiện lock quá 1h hoặc tiến trình chủ (`pid`) đã chết:
    1. Chuyển lock vào thư mục cách ly (`~/.codex/device-locks-reaped/`).
    2. Tự động chạy `am force-stop` com.ss.android.ugc.trill và `input keyevent 3` về Home an toàn.
- **Coordinator TUYỆT ĐỐI CẤM làm thay việc của Reaper** bằng cách tự ý bẻ lock hay force-stop sớm.

### Rule 4: Khóa cứng hai chiều ở tầng code (Hard Code Enforcement)
- **Triệt tiêu toàn bộ cờ opt-in bypass:** Trong mọi consumer script (như `social_reg_v1.py`), xóa bỏ `os.environ.get("DEVICE_LOCK_ENABLED")`. Luôn gọi `acquire_device_lock(..., user_authorized=True)`.
- **Cổng chặn entrypoint:** Đầu hàm `register()` hoặc runner entrypoint bắt buộc acquire lock thành công:
  ```python
  dev_lease = _acquire_social_device_lock_or_skip(stt, device_id, "register")
  if dev_lease is None:
      log(f"⚠ STT {stt} đang bị khóa bởi tiến trình/cron khác -> DỪNG để đảm bảo an toàn.")
      return False
  ```
  Nếu máy đang có tiến trình khác giữ lock -> Safe Abort ngay lập tức, không được chạm vào thiết bị.
  Khối `finally:` tự động gọi `dev_lease.release()` giải phóng sạch sẽ.

---

## 3. Checklist Điều Phối Tránh Phá Hoại (Coordinator Safe-Dispatch)
Trước khi gửi bất kỳ lệnh nào can thiệp máy $N$:
1. Đã kiểm tra file `~/.codex/device-locks/machine_<N>.lock.json` chưa?
2. Có tiến trình nào (`run_tiktok.py`, `run_batch_live_2fa.py`, `social_reg_v1.py`) đang giữ PID sống trên máy không?
3. Nếu có lock khác: Dừng ngay, cấm can thiệp, cấm force-stop, cấm bẻ lock.
4. Nếu máy rảnh: Acquire lock chuẩn trước rồi mới dispatch lệnh can thiệp.
