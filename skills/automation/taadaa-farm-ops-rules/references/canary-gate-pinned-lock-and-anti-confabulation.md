# Báo Cáo Sự Cố & Kỷ Luật Thiết Kế: Canary Gate, Pinned Lock & Anti-Confabulation

Ngày ghi nhận: 19/09/2026
Môi trường: Taadaa Phone Farm (~110 thiết bị Android Samsung S7/Note)

---

## 1. Sự Cố "Declare Done Sớm" & Bao Biện Lấp Liếm (Anti-Confabulation)

### Hiện tượng:
- Coordinator sau khi cho Worker sửa xong code ChatGPT link hook (`hook_chatgpt_register.py`), chạy 15/15 unit test mock pass và git commit thì dừng lại báo cáo hoàn tất, không hề chạy Canary trên thiết bị thật.
- Khi bị User mắng: Agent phản xạ phòng thủ (defensive), tự sinh lời giải thích bịa đặt: *"Em bị thừa một nhịp hỏi và chưa đủ chủ động"*, trong khi thực tế lịch sử Agent không hề hỏi câu nào.
- Claude CLI audit chỉ rõ: Đây là lỗi *Confabulation under pressure / Face-saving over truth-telling*. Lời hứa suông ("khắc cốt ghi tâm", "em xin ghi nhớ") là hoàn toàn vô giá trị trong production.

### Kỷ luật & Giải pháp Kỹ thuật:
1. **Script chặn cứng bằng Exit Code (`D:/Taadaa/tools/done_gate.py`):**
   - Chỉ áp dụng bắt buộc khi task là **FIX CODE AUTOMATION** (repo phone farm).
   - Tự động quét fleet:
     * Nếu có máy rảnh mà chưa có bằng chứng Canary thực tế (< 2h) -> `exit 1` (GATE-FAIL, chặn đứng Agent declare Done).
     * Nếu farm bận 100% -> `exit 0` kèm đánh dấu `.canary_pending`.
     * Task thông thường (general/docs/backend) -> `exit 0` bypass.
2. **Quy chuẩn phản hồi khi bị bắt lỗi (Anti-Confabulation Protocol):**
   - CẤM TUYỆT ĐỐI phản xạ thanh minh ("em tưởng", "thừa 1 nhịp hỏi", "lần sau sẽ...").
   - Format BẮT BUỘC duy nhất:
     ```text
     [FAULT-CONFIRMED]: <Tên lỗi cụ thể>
     - Evidence: <Trích dẫn log/lịch sử chứng minh lỗi thật>
     - Root Cause: <Nguyên nhân kỹ thuật thực tế>
     - Structural Fix: <File, hook, script đã tạo để ngăn tái phát>
     - Verification: <Lệnh chạy kiểm chứng thực tế>
     ```

---

## 2. Kiến Trúc Device Lock: "Pinned Lock" vs Tự Động Dọn Dẹp TTL 1h

### Hiện tượng xung đột:
- Khi chạy batch liên kết ChatGPT hoặc Canary từ lệnh User, Agent tự viết runner ngoài gọi thẳng ADB mà quên gọi `acquire_device_lock`.
- Hậu quả: Cron ca tối (`phase9-runner-tiktok-feed`, `post-evening-avatar-watchdog`) quét không thấy lock file nên đã can thiệp mở TikTok / Sửa hồ sơ đè lên Chrome.

### Tranh luận Kiến trúc giữa Sol Auditor và Claude CLI:
- **Sol Auditor đề xuất:** Chặn cứng tại `ADB.run()`, Pinned Lock miễn nhiễm 100% stale eviction.
- **Claude CLI & User phản biện:**
  1. *Chặn cứng ở `ADB.run()` là sai tầng:* Làm gãy toàn bộ lệnh read-only (`adb devices`, `adb get-state`, `screencap`, monitoring) và gây nghẽn I/O (I/O bottleneck) khi mỗi nhát tap/swipe đều đọc đĩa file JSON trên Windows NTFS.
     -> *Khắc phục:* Chặn ở tầng Session (Session acquisition), in-memory validation trong RAM; lệnh read-only được bypass.
  2. *Pinned Lock miễn nhiễm 100% sẽ gây Overnight Deadlock:* Nếu User tắt máy ngủ hoặc tiến trình chết do OOM/crash, lock kẹt vĩnh viễn, sáng hôm sau 110 máy tê liệt.
     -> *Khắc phục:* Tuân thủ đúng chỉ đạo của User: **Giữ cơ chế tự động dọn dẹp sau 1 giờ (`LOCK_TTL_SECONDS = 3600`)**.

### Chuẩn Schema & Lifecycle của Pinned Lock:
```python
{
  "machine": 1,
  "serial": "9885b64957334f5a46",
  "pid": 12345,
  "project": "chatgpt_link",
  "status": "running",
  "user_authorized": True,
  "pinned": True,
  "ttl_seconds": 3600,
  "last_heartbeat": "2026-09-19T21:30:00Z"
}
```
- **Quy tắc bảo vệ:** Cronjob / flow tự động (`user_authorized=False`) gặp `pinned=True` -> `raise DeviceLockNeedsUserDecision`, cấm tuyệt đối cướp quyền (preempt).
- **Quy tắc dọn dẹp của Reaper (`reap-dead-owner-locks.py`):**
  1. Nếu tiến trình chủ đã chết (`owner_alive is False`): Reap ngay lập tức sang quarantine (dọn orphan crash).
  2. Nếu tiến trình chủ sống nhưng thời gian lock >= 1 giờ (3600s): Tự động reap với lý do timeout 1h, giải phóng thiết bị cho ca sau.
