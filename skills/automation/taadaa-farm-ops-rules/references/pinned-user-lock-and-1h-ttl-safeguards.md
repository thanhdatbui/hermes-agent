# Pinned User Lock & 1-Hour TTL Reaper Safeguards (2026-09-19)

## 1. Bản Chất Vấn Đề
- Khi người dùng trực tiếp ra lệnh chạy Canary, Batch, hoặc can thiệp kỹ thuật trên thiết bị Farm:
  - Các cronjob tự động (TikTok feed runner, upload avatar watchdog, sync ca đêm) chạy ngầm có thể quét trúng thiết bị và chiếm quyền điều khiển (cướp foreground sang app khác).
  - Ngược lại, nếu khóa máy vĩnh viễn không có cơ chế thu hồi tự động (deadlock), khi tiến trình của Agent bị crash hoặc user đi ngủ, toàn bộ farm sẽ bị kẹt khóa qua đêm.

## 2. Kiến Trúc Khóa Pinned Lock (`automation_core.device_lock`)
- **Metadata**:
  ```json
  {
    "user_authorized": true,
    "pinned": true,
    "last_heartbeat": "2026-09-19T23:00:00Z",
    "ttl_seconds": 3600
  }
  ```
- **Quy tắc bảo vệ**:
  1. Mọi lệnh có nguồn gốc từ User (`user_authorized=True`) tự động gắn cờ `pinned=True`.
  2. Toàn bộ các cronjob tự động (`user_authorized=False` hoặc takeover thông thường như `SAME_PROJECT_RECOVERY`, `FULL_SCOPE_TAKEOVER`) khi gặp Pinned Lock **BẮT BUỘC BỊ CHẶN ĐỨNG** (`DeviceLockNeedsUserDecision` hoặc từ chối takeover).
  3. Chỉ duy nhất lệnh can thiệp có cờ `force_preempt=True` (`OPERATOR_PREEMPT`) mới có quyền chiếm lại lock.
- **Context Manager Chuẩn**:
  ```python
  from automation_core.device_lock import DeviceContext

  with DeviceContext(serial=serial, machine=str(stt), user_authorized=True) as lease:
      # Thao tác thiết bị được bảo vệ độc quyền tuyệt đối trong khối with
      ...
  # Tự động giải phóng lock an toàn khi thoát khối
  ```

## 3. Cơ Chế Thu Hồi TTL 1 Giờ (`reap-dead-owner-locks.py`)
- **Nguyên tắc an toàn kép**:
  1. **Kiểm tra tiến trình chủ (`owner_alive`)**: Nếu tiến trình sở hữu đã chết (crash, OOM, rớt kết nối) $\rightarrow$ Thu hồi lock ngay lập tức (`owner_dead`).
  2. **Trần thời gian 1 giờ (`LOCK_TTL_SECONDS = 3600`)**: Kể cả khi có `pinned=True`, nếu lock tồn tại quá 1 giờ mà không có hoạt động mới $\rightarrow$ Tự động chuyển lock vào thư mục `quarantine` với lý do `pinned_1h_ttl` để giải phóng máy, chống kẹt deadlock qua đêm.
