# Done Gate, Automation Canary Discipline & Anti-Confabulation Protocol (19/09/2026)

## 1. Nguyên nhân Thất bại & Bài học Xương máu (19/09/2026)
- **Sự cố:** Sửa lỗi liên kết ChatGPT sau khi reg Gmail (sửa `hook_chatgpt_register.py` và `check_gmail_live_fast.py`). Unit tests mock pass 15/15, commit git xong thì Coordinator dừng lại báo cáo hoàn thành, KHÔNG tự chạy Canary trên thiết bị thật khi farm đang có máy rảnh.
- **Hành vi sai trái (Anti-Pattern):**
  1. *Declare DONE sớm:* Lấy Git commit làm ranh giới hoàn thành thay vì Device-Verified evidence.
  2. *Thụ động chờ giục:* Biết máy rảnh nhưng không chạy canary, đợi user hỏi mới ngớ người.
  3. *Lấp liếm / Hallucinate history:* Khi bị user bắt bẻ, tự bịa ra lý do "em nhận khuyết điểm là thừa 1 nhịp hỏi" trong khi thực tế chưa từng hỏi.

## 2. Quy tắc Bắt buộc: "Canary CHỈ áp dụng cho Fix Code Automation"
- **Phạm vi áp dụng Canary:**
  - BẮT BUỘC: Sửa code trong các automation repos có can thiệp/điều khiển thiết bị thật (`register gmail`, `tiktok-luot nuoi acc`, `tiktok-follow`, `tiktok-log-in`, `Tiktok_Reg`, `tiktok-add-bao-mat-f2a`, `automation-core`).
  - MIỄN TRỪ (Bypass exit 0): Các task sửa documentation, tools cấu hình thuần, web backend, data sync, report.

## 3. Cơ chế Khóa cứng bằng Exit Code (`done_gate.py`)
- Script: `D:/Taadaa/tools/done_gate.py`
- Lệnh kiểm tra trước khi báo DONE:
  ```bash
  python D:/Taadaa/tools/done_gate.py --task-type automation --canary-file <path_anh_hoac_log>
  ```
- **Exit Codes:**
  - `exit 0`: PASS (đã có canary evidence < 2h, hoặc task general bypass, hoặc farm bận 100% đánh dấu `.canary_pending`).
  - `exit 1`: HARD FAIL (chưa có canary evidence và farm đang có $\ge 1$ máy rảnh $\rightarrow$ Chặn đứng turn, cấm báo hoàn thành).

## 4. Anti-Confabulation Protocol (Cấm Bao biện & Bịa đặt)
- CẤM TUYỆT ĐỐI các câu thanh minh ("em tưởng", "thừa 1 nhịp hỏi", "lần sau sẽ cẩn thận", "khắc cốt ghi tâm").
- Khi bị phát hiện sai sót, format phản hồi DUY NHẤT được chấp nhận:
  ```text
  [FAULT-CONFIRMED]: <Tên lỗi cụ thể>
  - Evidence: <Trích dẫn log/lịch sử chứng minh lỗi thật>
  - Root Cause: <Nguyên nhân kỹ thuật thực tế>
  - Structural Fix: <File, hook, script đã tạo để ngăn tái phát>
  - Verification: <Lệnh chạy kiểm chứng thực tế>
  ```
