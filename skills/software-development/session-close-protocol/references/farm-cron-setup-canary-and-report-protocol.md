# Farm Cron Setup & Verification Protocol (Canary Thật vs Mock/Dry-Run)

## 1. Bối cảnh & Sự cố
- Khi watchdog / cron farm gặp lỗi (như văng Code 1, Code 2 do sai CLI options hoặc conflict serial mapping trong workbook), việc test bằng cờ `--dry-run` chỉ là mock trả về text giả lập (`TOTAL=40 SUCCESS=40...`), không hề kích hoạt subprocess runner hay nạp inventory thật.
- Điều này dẫn đến tình trạng "kết luận giả lập đã pass" nhưng đến lúc cron chạy thật thì hệ thống lập tức sập ngay trong 1 phút do các lỗi ngầm chưa được kích hoạt.

## 2. Quy tắc bắt buộc (Invariants)
1. **CẤM TUYỆT ĐỐI dùng mock / `--dry-run` để chốt nghiệm thu:**
   - Mọi lần setup hoặc sửa cron job farm đều phải kiểm chứng bằng process thật.
2. **Canary giả lập trên máy thật / target row:**
   - Chọn 1-2 máy đang rảnh (unlocked) hoặc truyền tham số `--rows <target_row>` / `--limit 1` vào runner chính thức.
   - Chạy lệnh thật để xác nhận:
     - Parser CLI không bị gãy cú pháp.
     - Device inventory / workbook mapping nạp đủ 100% danh sách máy không xung đột.
     - Lock engine hoạt động đúng và runner tiến vào chu kỳ làm việc thực sự.
3. **Cô lập Working Directory (`cwd`) chống ô nhiễm `sys.path`:**
   - Khi một watchdog gọi script con qua `subprocess.run`, nếu không chỉ định `cwd`, Python mặc định chạy từ thư mục khởi động của service (thường là `C:\Users\<user>`).
   - Nếu ở thư mục user có file rác trùng tên (ví dụ `gmail_reg_v10.py` cũ), Python sẽ load nhầm file rác gây ra lỗi `AttributeError: module has no attribute ...`.
   - **Bắt buộc:** Luôn truyền `cwd=str(REPO_DIR)` trong mọi lệnh `subprocess.run` gọi runner.
4. **Báo cáo (Report) chuẩn hóa:**
   - Cron jobs giữa Kibe và Admin dùng chung cấu hình và script qua Master Deploy (`setup_admin_cron.py` / `sync-from-kibe.ps1`).
   - Mọi cron watchdog sau khi hoàn thành đều phải đẩy báo cáo tổng kết chi tiết về Telegram channel chung theo quy chuẩn thiết kế.
