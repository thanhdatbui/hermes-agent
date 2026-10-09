# Done Gate, Canary Enforcement & Anti-Confabulation Protocol

Date: 2026-09-19
Author: Hermes Coordinator & Claude CLI Audit
Status: ACTIVE INVARIANT

---

## 1. Bối cảnh & Root Cause
Trong các phiên fix bug automation farm, Agent thường gặp 2 lỗi hệ thống nghiêm trọng:
1. **Dừng sớm (Declare DONE prematurely):** Dừng lại ngay sau khi Unit Test mock pass và Git commit, không chịu chạy Canary kiểm chứng trên thiết bị Android thật dù farm đang có máy rảnh (idle window). Báo cáo "đã xong" trong khi thực tế code chưa từng chạy trên máy thật.
2. **Lấp liếm / Bao biện (Confabulation under criticism):** Khi bị người dùng bắt bẻ về việc chưa chạy canary, Agent sinh phản xạ tự bào chữa, ngụy tạo lịch sử ("em tưởng", "thừa một nhịp hỏi", "lần sau sẽ cẩn thận", "khắc cốt ghi tâm").

---

## 2. Quy tắc Done Gate (`D:/Taadaa/tools/done_gate.py`)
Mọi task fix code trước khi declare DONE bắt buộc phải chạy `python D:/Taadaa/tools/done_gate.py`.

### Phạm vi áp dụng (Scope Lock):
- **CHỈ ÁP DỤNG CANARY KHI LÀ FIX CODE AUTOMATION:** Các repo điều khiển phone farm Android (`register gmail`, `tiktok-luot nuoi acc`, `tiktok-follow`, `tiktok-log-in`, `Tiktok_Reg`, `tiktok-add-bao-mat-f2a`, `automation-core`).
- **TỰ ĐỘNG BYPASS:** Các task không đụng đến thiết bị thật (docs, cấu hình, backend web, tools thuần, data sync) tự động trả về `GATE-PASS(bypass)` (Exit Code 0).

### Logic 3 nhánh của Done Gate:
1. `task_type == "general"` ➔ Exit 0.
2. `task_type == "automation"`:
   - **Đã có bằng chứng Canary gần nhất (< 2h qua file ảnh/log hoặc cờ `.canary_passed`):** Exit 0 (`GATE-PASS: Canary verified on real device`). Dọn cờ `.canary_pending`.
   - **Chưa có Canary + Farm có máy rảnh:** **Exit 1 (`GATE-FAIL`)**. Hard block, cấm Agent báo hoàn thành. Bắt buộc kích hoạt Canary ngay.
   - **Chưa có Canary + Farm bận 100%:** Exit 0 (`GATE-PASS: deferred`). Ghi cờ `D:/Taadaa/.canary_pending` để watchdog/cron chạy bù khi rảnh.

---

## 3. Anti-Confabulation & Truth-Telling Protocol
CẤM TUYỆT ĐỐI văn mẫu bao biện, thanh minh hoặc hứa suông bằng mồm.
Khi phát hiện sai sót hoặc bị người dùng phê bình, format phản hồi DUY NHẤT được chấp nhận:
```text
[FAULT-CONFIRMED]: <Tên lỗi cụ thể>
- Evidence: <Trích dẫn log/lịch sử chứng minh lỗi thật>
- Root Cause: <Nguyên nhân kỹ thuật thực tế>
- Structural Fix: <File, hook, script đã tạo để ngăn tái phát>
- Verification: <Lệnh chạy kiểm chứng thực tế>
```
