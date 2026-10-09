# Cạm Bẫy Phân Tích Lan Man Khi Canary Gặp Lỗi Thiết Bị (SWITCHER_OPEN_FAILED) (07/09/2026)

## 1. Bối cảnh & Hiện tượng sự cố
- **Phiên thực tế:** Trưa 07/09/2026 (11h00 – 12h33).
- **Mục tiêu:** Chạy Live Canary kiểm chứng Add 2FA trên Máy 1 (`ginnyhanstei80`).
- **Hiện tượng lỗi:** Tiến trình chạy runner `run_batch_live_2fa.py --limit 1 --live` chạm máy và kết thúc sau 3 phút với kết quả terminal:
  ```text
  Kết quả
  machine | source_row | username | status | reason
  1 | 5 | g************* | failed | SWITCHER_OPEN_FAILED
  ```
- **Hành vi sai lệch của Worker (Anti-Pattern - Runaway Analysis Paralysis):**
  - Thay vì dừng lại và báo cáo ngay kết quả thất bại kèm ảnh hiện trường cho Coordinator, worker subagent tự ý mở rộng phạm vi task sang "điều tra vì sao switcher không mở được".
  - Worker gọi `computer_use` (bị backend timeout), gọi `search_files` quét đĩa diện rộng với path MSYS `/d/Taadaa/...` (dính lỗi `os error 2` và tool loop warning liên tiếp), rồi đào sâu đọc `automation-core/src/automation_core/tiktok/account_switcher.py` và `kibe.yaml`.
  - Hậu quả: Worker ngâm phiên suốt hơn 40 phút, thực hiện 23+ tool calls vô ích trong khi session chính bị treo, khiến người dùng bức xúc tột độ (*"Clgt t gửi từ 11h h 12h33 k xong lại tiếp tục sa đà vào over engineer r phải k"*).

---

## 2. Nguyên nhân cốt lõi
1. **Thiếu ranh giới dừng (Termination Boundary):** Nhiệm vụ của worker ở bước Canary B4 là **thực thi và ghi nhận kết quả**. Khi runner trả về kết quả terminal (`failed` / `skipped` / `blocked`), nhiệm vụ đã hoàn thành về mặt thực thi kiểm chứng. Việc tự ý chuyển task thành "sửa lỗi switcher" là vi phạm nghiêm trọng quy tắc Scope Lock.
2. **Bẫy quét đĩa Windows bằng path MSYS:** Worker dùng tool `search_files` với đường dẫn dạng Linux `/d/Taadaa/...` trên môi trường Windows khiến ripgrep văng lỗi `IO error: The system cannot find the file specified (os error 2)` và rơi vào vòng lặp retry tool lặp lại.

---

## 3. Quy tắc cưỡng chế bắt buộc (Strict Enforcement Rules)

1. **Terminal Result = Stop & Report Immediately:**
   - Khi worker được giao chạy Canary / Live Run kiểm chứng: Nếu runner trả về kết quả trạng thái máy (kể cả `failed` với bất kỳ lý do nào như `SWITCHER_OPEN_FAILED`, `DEVICE_LOCK_UNAVAILABLE`, `PROFILE_NOT_REACHED`):
   - **BẮT BUỘC:** Chụp screencap hiện trường $\rightarrow$ In output runner $\rightarrow$ Kết thúc phiên ngay trong vòng tối đa 2 tool calls.
   - **CẤM TUYỆT ĐỐI:** Không tự ý điều tra ngược vào `automation-core`, không đọc file cấu hình hệ thống, không tự thử nghiệm các tool ngoài luồng (`computer_use`, `search_files` toàn đĩa).

2. **Quyền quyết định thuộc về Coordinator & User:**
   - Việc thiết bị fail do tài khoản không có trong switcher, do UI TikTok đổi hay do lỗi hệ thống là quyết định phân tích ở tầng Coordinator và người dùng. Worker không được tự ý "thay quyền quyết định" để điều tra lan man.

3. **Chỉ thị dập tắt Analysis Paralysis trong Prompt Delegate:**
   - Khi Coordinator giao task chạy Canary, BẮT BUỘC chèn chỉ thị:
     `[CANARY TERMINATION CONTRACT]: Runner trả về kết quả (thành công hoặc thất bại) BẮT BUỘC dừng lại, chụp screencap và báo cáo ngay. CẤM TUYỆT ĐỐI tự ý đào sâu điều tra hoặc đọc thêm file ngoài scope khi runner đã exit.`
