# Device Lock Two-Way Coordination, Manual Test Hygiene & Reaper Policy

## 1. Nguyên Tắc Cốt Tử: Khóa Hai Chiều (Cron vs Script vs Coordinator)

Hệ thống Phone Farm Taadaa có nhiều tiến trình chạy song song:
- Cron nuôi acc theo lịch (`run_tiktok.py --mode multi-machine-feed-session`).
- Batch jobs (add 2FA, upload video, change info).
- Script chạy ad-hoc / test thủ công (`social_reg_v1.py <N>`, `tiktok_login_v1.py <N>`).
- Coordinator giám sát & điều phối.

### Cơ chế bảo vệ bất khả xâm phạm:
1. **Mọi script can thiệp máy BẮT BUỘC acquire `device_lock` chuẩn của farm (`machine_<N>.lock.json`):**
   - **CẤM TUYỆT ĐỐI** dùng cờ opt-in kiểu `os.environ.get("DEVICE_LOCK_ENABLED")` khiến script chạy lẻ bỏ qua acquire lock. Phải hardcode `user_authorized=True`.
   - Khi script chạy, nếu máy đã có file `machine_<N>.lock.json` của tiến trình khác có PID đang sống (`psutil.pid_exists(pid)`) -> **PHẢI DỪNG LẠI NGAY LẬP TỨC (Safe-Skip / Abort)**. Cấm cố chạy tiếp.
2. **Coordinator TUYỆT ĐỐI KHÔNG dùng lệnh ADB phá hoại trên máy đang có lock:**
   - Khi quan sát máy có màn hình lạ (ví dụ: màn hình Authenticator 2FA, màn hình upload): **DOUBT → FREEZE → REPORT → WAIT**.
   - **CẤM** tự tiện gõ lệnh ADB thô (`am force-stop`, `input keyevent 3`, `input tap`) trên máy mà một tiến trình khác đang sở hữu lock.
   - Thao tác `am force-stop` chỉ được phép thực thi bởi chính tiến trình đang sở hữu lock của máy đó để dọn dẹp app trước/sau phiên chạy (hygiene).

---

## 2. Cron Tháo Lock 1 Giờ (Reaper Policy)

Hệ thống đã có sẵn script thu hồi lock và dọn dẹp an toàn:
- File thực thi: `D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py`.
- Watchdog: `D:/Taadaa/tools/watch_device_locks.py`.

### Logic xử lý:
- Quét toàn bộ file `machine_*.lock.json` tại `~/.codex/device-locks/`.
- **Nếu PID chủ sở hữu đã chết (`owner_dead`):** Dọn lock ngay lập tức (move sang thư mục quarantine `~/.codex/device-locks-reaped/`) và chạy dọn dẹp ADB (`am force-stop com.ss.android.ugc.trill` + `input keyevent 3` về HOME).
- **Nếu PID chủ sở hữu còn sống:**
  - Nếu tuổi lock < 1 giờ (3600 giây): Giữ nguyên, KHÔNG ĐƯỢC PHÉP THÁO.
  - Nếu tuổi lock >= 1 giờ (timeout/treo): Bị xem là kẹt quá hạn (timeout) -> mới được phép reap và dọn về HOME.
- **Nếu trạng thái `blocked` (giữ hiện trường):** Giữ tối đa 1 giờ cho operator triage trước khi reap.
