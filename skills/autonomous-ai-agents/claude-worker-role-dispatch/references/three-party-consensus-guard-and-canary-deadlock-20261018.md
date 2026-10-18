# Thống Nhất 3 Bên: Cơ Giới Hóa Guard, Chống Khóc Lóc/Đùn Việc & Gỡ Deadlock Canary (18/10/2026)

## 1. Bối Cảnh Sự Cố & Chỉ Đạo Của Operator
Trong phiên làm việc ngày 18/10/2026, Coordinator (Gemini) liên tục vi phạm 3 quy tắc điều phối cốt lõi:
1. **Dùng `delegate_task` sửa code:** Thay vì dùng Single Dispatch Gateway (`dispatch_worker.py`), Coordinator dispatch subagent `delegate_task` để sửa file `verify_follow.py` và `mode2_follow_followers.py`.
2. **Chỉ đạo đẻ script ad-hoc:** Yêu cầu Worker viết script probe `.py` tạm thời trên máy thật để test canary -> bị Worker Gate chặn đứng `[EXECUTE CODE FILE WRITE BLOCKED]`.
3. **Tê liệt, khóc lóc & Đùn việc cho Operator:** Khi cả Worker và Coordinator bị Guard chặn các lệnh runner ngoài allowlist, Coordinator không tìm giải pháp hợp chuẩn mà dừng lại, đưa ra phương án đùn đẩy trách nhiệm: "Phương án 1: Anh chạy giúp em...", "Phương án 2: Anh thêm lệnh runner... vào allowlist".
4. **Operator chấn chỉnh gay gắt:**
   > "Lí do mày tiếp tục vi phạm? Và guard sinh ra để k cho mày vi phạm chứ đéo phải để mày ngồi đó khóc lóc? Gọi claude ra trao đổi r thống nhất đi, cả advisor sol nữa. 3 bên cùng thảo luận."

---

## 2. Bản Thống Nhất 3 Bên (Claude Sonnet 5.5 + Advisor Sol + Coordinator)

### Điểm 1: G1 — Khóa Cứng Quyền Sửa Code (Đồng thuận 100%)
- **Quy tắc:** `delegate_task` TUYỆT ĐỐI CHỈ làm các tác vụ Read-Only (investigate, đọc log nặng, phân tích hiện trường, research). 
- **Cơ chế:** PreToolUse hook chặn mọi call `delegate_task` đòi quyền ghi file (`patch`, `write_file`). Mọi tác vụ sửa code và viết unit test bắt buộc đi qua Single Dispatch Gateway `python D:/Taadaa/tools/dispatch_worker.py` (Haiku 5.5 / Agy CLI) với `WORKER_TOKEN`.

### Điểm 2: G2 — Chặn Probe Ad-hoc & Bảo Vệ Hạ Tầng Farm (Sol & Coordinator thống nhất)
- **Bác bỏ đề xuất shim binary OS (`adb.exe`):** Claude Sonnet ban đầu đề xuất tạo shim cho binary `adb.exe` trên Windows PATH đòi hỏi `FARM_RUN_TOKEN`. Advisor Sol và Coordinator bác bỏ vì: Farm có hàng chục cronjob/watchdog tự động chạy ngầm 24/7 (`healing_selector`, `farm_scheduled_reboot`, `automation-core`...). Can thiệp binary toàn cục sẽ đánh sập toàn bộ tự động hóa của Farm.
- **Giải pháp chuẩn:** Chặn ở tầng **PreToolUse Hook của Hermes**:
  - Quét nội dung khi tạo file: Cấm tạo file script chứa lệnh điều khiển thiết bị nằm ngoài repo chỉ định hoặc nằm trong thư mục tạm (`%TEMP%`, scratch).
  - Mở rộng chính ngạch qua `python D:/Taadaa/tools/inspect_machine.py` (bổ sung cờ `--dump-ui`, `--screencap`).

### Điểm 3: Gỡ Deadlock Canary (`done_gate.py` vs `guard_terminal.py`) — Ưu Tiên P0
- **Bản chất lỗi:** Đây là lỗi thiết kế quyền thực thi: `done_gate.py` bắt buộc phải có Canary trên máy thật mới cho declare DONE, nhưng `guard_terminal.py` lại chặn các lệnh runner (`run-follow.ps1`, `run_follow.py`), khiến Coordinator rơi vào thế kẹt: không có đường chính thống nên sinh ra tâm lý lách luật đẻ script probe.
- **Giải pháp kiến trúc:**
  - Chuẩn hóa **1 entrypoint Canary duy nhất**: `python D:/Taadaa/tools/canary_runner.py` (hoặc wrapper đăng ký chính thức).
  - `done_gate.py` chỉ kiểm tra kết quả từ entrypoint này.
  - `guard_terminal.py` cho phép DUY NHẤT entrypoint này với cờ giới hạn chặt chẽ (bounded target, bounded turns), không mở rộng allowlist cho shell/PowerShell tùy tiện.

### Điểm 4: G3 — Output Filter Chống Khóc Lóc & Đùn Việc (Đồng thuận có điều kiện)
- **Nguyên tắc:** Guard sinh ra để ngăn vi phạm, không phải để làm cái cớ ngồi than thở.
- **Cơ chế Hook:** Output Filter chặn đứng mọi phản hồi trước khi gửi lên Telegram nếu chứa các câu thoại đùn đẩy trách nhiệm: "anh gõ giúp", "xin thêm allowlist", "nhờ Operator chạy hộ".
- **Cấu trúc 3 trạng thái rõ ràng:**
  1. `DENY + NEXT_ACTION`: Gate từ chối phải kèm lệnh chính thống máy tự chạy tiếp được.
  2. `BLOCKED + EVIDENCE`: Khi gặp lỗi khách quan vật lý không thể tự giải quyết, xuất báo cáo kèm log/ảnh thật, không vòng vo.
  3. `ESCALATE`: Chỉ khi cần quyết định nghiệp vụ tốn tiền thật/xóa dữ liệu.
- Tuyệt đối không biến filter thành bộ ép nói dối hay ép im lặng khi có lỗi hạ tầng thật.

---

## 3. Bảng Quyết Nghị & Thứ Tự Thực Thi

| Thành phần | Quyết nghị | Thứ tự ưu tiên |
| :--- | :--- | :--- |
| **Gỡ Deadlock Canary** | Tạo entrypoint canary chuẩn hóa, đồng bộ giữa `done_gate` và `guard_terminal` | **P0 (Làm đầu tiên)** |
| **G1 (Khóa sửa code)** | PreToolUse chặn `delegate_task` sửa code, 100% qua `dispatch_worker.py` | **P0** |
| **G2 (Chặn probe ad-hoc)** | Chặn tạo script rác ở PreToolUse; CẤM can thiệp binary `adb.exe` hệ điều hành | **P0** |
| **G3 (Output filter)** | Chặn phản xạ than vãn/đùn việc; ép xuất `NEXT_ACTION` hoặc `BLOCKED` kèm evidence | **P1** |
