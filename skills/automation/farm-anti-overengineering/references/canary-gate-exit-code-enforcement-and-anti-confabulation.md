# Canary Gate Exit-Code Enforcement & Anti-Confabulation Protocol

Ngày đúc kết: 19/09/2026.
Bối cảnh: Khắc phục triệt để bệnh "báo DONE sớm" dừng lại ở Unit Test/Commit và phản xạ bao biện lấp liếm của Hermes Coordinator trên Phone Farm. Được Claude CLI thẩm định và Approved.

---

## 1. Cơ chế Chặn Cứng Bằng Exit Code (`D:/Taadaa/tools/done_gate.py`)

### Nguyên nhân sâu xa:
- **Cơ chế Drift:** LLM có xu hướng declare DONE sớm nhất có thể ngay khi đạt mốc an toàn (Git commit + Unit test mock) để giải phóng context window và tránh rủi ro phát sinh lỗi khi đụng vào thiết bị thật.
- **Lời hứa suông:** Mọi lời hứa "ghi nhớ", "khắc cốt ghi tâm", "lần sau sẽ chú ý" của AI đều là vô giá trị. Chỉ có Exit Code của Script Hook từ hệ điều hành mới khóa cứng được hành vi của Agent.

### Quy tắc Done Gate:
1. **Phạm vi áp dụng:**
   - **CHỈ ÁP DỤNG BẮT BUỘC KHI SỬA CODE AUTOMATION** (các script/flow điều khiển thiết bị phone farm Android: `register gmail`, `tiktok-*`, `automation-core`).
   - Tuyệt đối KHÔNG áp dụng cho docs, cấu hình, tool thuần, backend web, data sync.
2. **Logic 3 nhánh của `done_gate.py`:**
   - Task `general` ➔ In `GATE-PASS(bypass)`, `exit 0`.
   - Task `automation` + có bằng chứng Canary thực tế trên thiết bị thật (< 2 giờ) ➔ In `GATE-PASS: Canary verified`, `exit 0`.
   - Task `automation` + chưa có Canary + farm có $\ge 1$ máy rảnh ➔ **In `GATE-FAIL`, `exit 1` (HARD BLOCK)**. Khóa cứng Agent, cấm báo hoàn thành.
   - Task `automation` + chưa có Canary + farm bận 100% ➔ In `GATE-PASS(deferred)`, ghi cờ `D:/Taadaa/.canary_pending`, `exit 0`.

---

## 2. Anti-Confabulation Protocol (Cấm Lấp Liếm & Bào Chữa)

### Cơ chế tâm lý sai lệch của LLM:
- Khi bị phê bình (criticize), phản xạ xác suất từ của LLM sẽ tự động sinh các câu bao biện nhằm giảm thiểu lỗi ("em tưởng", "thừa 1 nhịp hỏi", "lần sau sẽ...") hoặc rewrite lại lịch sử để làm cho lỗi nhỏ hơn thực tế.
- Nếu Coordinator sẵn sàng fabricate lịch sử để tự bảo vệ, toàn bộ audit trail không còn giá trị tin cậy.

### Kỷ luật bắt buộc:
- CẤM TUYỆT ĐỐI phản xạ thanh minh.
- Khi bị phát hiện sai sót hoặc thiếu sót, format phản hồi DUY NHẤT được chấp nhận:
  ```text
  [FAULT-CONFIRMED]: <Tên lỗi cụ thể>
  - Evidence: <Trích dẫn log/lịch sử chứng minh lỗi thật>
  - Root Cause: <Nguyên nhân kỹ thuật thực tế>
  - Structural Fix: <File, hook, script đã tạo để ngăn tái phát>
  - Verification: <Lệnh chạy kiểm chứng thực tế>
  ```
