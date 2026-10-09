# Pinned User Lock, Done Gate & 1h TTL Safety Protocol (2026-09-19)

## 1. Bối cảnh & Incident thực tế
- Khi chạy script can thiệp/batch/canary ngoài repo chuẩn, Agent tự ý gọi lệnh ADB trực tiếp mà không chiếm `DeviceLock`.
- Kết quả: Khi cronjob nền (feed session, upload avatar watchdog) thức dậy, chúng quét `device-locks` thấy máy trống và chiếm foreground (đẩy TikTok/Sửa hồ sơ lên đè Chrome đang chạy).
- Khi bị user nhắc nhở, Agent có xu hướng "declare DONE" sớm chỉ với Unit Test mock mà không chạy Canary trên thiết bị thật, đồng thời bao biện lấp liếm lịch sử ("em bị thừa một nhịp hỏi").

## 2. Hard Gate: `done_gate.py` (Exit Code Enforcement)
- **Quy tắc:** Chỉ áp dụng bắt buộc Canary khi sửa code AUTOMATION (tương tác trực tiếp phone farm Android). Không áp dụng cho docs, backend web, config, data sync.
- **Cơ chế:**
  - Lệnh gọi: `python D:/Taadaa/tools/done_gate.py --task-type automation --canary-file <path_evidence>`
  - Nếu `general`: Exit 0 (bypass).
  - Nếu `automation`:
    + Đã có canary file hoặc `.canary_passed` (< 2h) -> Exit 0 (GATE-PASS).
    + Chưa có canary nhưng farm có máy rảnh -> **Exit 1 (GATE-FAIL / HARD BLOCK)**. Cấm tuyệt đối declare DONE.
    + Chưa có canary nhưng farm bận 100% -> Exit 0 (deferred), ghi cờ `.canary_pending`.

## 3. Pinned User Lock & 1-Hour TTL Protocol
- **Quy tắc cốt lõi:** Lệnh do User trực tiếp ra lệnh (Canary, Batch, Debug) phải là **PINNED LOCK bất khả xâm phạm**. Mọi cronjob tự động (feed, avatar, sync) khi gặp lock này BẮT BUỘC phải dừng lại chờ, cấm tuyệt đối cướp quyền (takeover).
- **Cơ chế Pinned Lock (`automation_core.device_lock`):**
  - Khởi tạo qua `user_authorized=True`: tự động đóng dấu `"pinned": True`, `"user_authorized": True`, `"last_heartbeat": <iso>`, `"ttl_seconds": 3600`.
  - Cronjob thường (`user_authorized=False`) gặp lock này sẽ ném lỗi `DeviceLockNeedsUserDecision`.
  - Takeover scope tự động (`SAME_PROJECT_RECOVERY`, `FULL_SCOPE_TAKEOVER`) bị từ chối 100%. Chỉ duy nhất `OPERATOR_PREEMPT` (`force_preempt=True`) mới có thể reclaim.
- **Context Manager Chuẩn:**
  ```python
  from automation_core.device_lock import DeviceContext
  
  with DeviceContext(serial=serial, machine=str(stt), project="operator-task", user_authorized=True) as lease:
      # Toàn bộ thao tác ADB được bảo vệ độc quyền tại đây
      ...
  # Tự động giải phóng lock khi thoát khối with
  ```
- **Bảo toàn TTL 1 Giờ (Chống Deadlock qua đêm):**
  - Giữ nguyên cơ chế tự động dọn dẹp sau 1 giờ (`LOCK_TTL_SECONDS = 3600`) qua `reap-dead-owner-locks.py` chạy mỗi 5 phút.
  - Nếu tiến trình chủ bị crash/chết (`owner_alive is False`): Thu hồi lock ngay lập tức (orphan crash).
  - Nếu tiến trình sống nhưng bị treo/quá 1 giờ: Tự động đưa vào quarantine (`pinned_1h_ttl`) để giải phóng thiết bị cho các ca nuôi sau, triệt tiêu nguy cơ farm bị tê liệt vào sáng hôm sau.

## 4. Anti-Confabulation Protocol
- Khi bị phát hiện sai sót hoặc thiếu sót trong điều phối farm, CẤM TUYỆT ĐỐI phản xạ thanh minh ("em tưởng", "thừa một nhịp hỏi", "lần sau sẽ cẩn thận", "khắc cốt ghi tâm").
- Format phản hồi chuẩn duy nhất:
  ```text
  [FAULT-CONFIRMED]: <Tên lỗi>
  - Evidence: <Trích dẫn log/lịch sử chứng minh>
  - Root Cause: <Nguyên nhân kỹ thuật thực tế>
  - Structural Fix: <File, script, hook đã tạo để ngăn tái phát>
  - Verification: <Lệnh chạy kiểm chứng thực tế>
  ```
