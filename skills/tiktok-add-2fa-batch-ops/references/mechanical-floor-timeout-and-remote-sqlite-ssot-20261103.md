# Mechanical Floor Timeout & Remote SQLite SSOT Invariants (2026-11-03)

## 1. Bài học về Sàn Timeout Cơ Học ($\ge 300\text{s}$)
- **Hiện tượng vi phạm:** Agent có xu hướng tự tiện nhồi cờ `--timeout 60` hoặc `timeout=60` vào các lệnh terminal gọi Advisor Council (`consult_advisor.py`), Claude CLI hoặc Planner/Worker do phản xạ sợ lệnh chạy lâu. Hậu quả là Claude CLI hoặc Sol bị ngắt ngang khi đang đọc context, dẫn đến báo cáo phiến diện một chiều hoặc timeout giả.
- **Biện pháp cơ giới hóa bắt buộc (Mechanical Enforcement):**
  * Không dựa vào "trí nhớ" hay "lời hứa".
  * Tất cả các hằng số timeout trong `gate_b_planner.py` (`GEMINI_TIMEOUT`, `CLAUDE_TIMEOUT`, `SOL_TIMEOUT`) và `consult_advisor.py` bắt buộc neo cứng $\ge 300\text{s}$.
  * Cơ chế Gate G15 (`Mechanical Floor Timeout 300s`) trong `gate_compliance_watchdog.py` tự động quét và đánh FAIL bất kỳ lệnh nào truyền timeout dưới 300s.
  * Khi gọi `terminal()` từ Coordinator cho các tác vụ tư vấn hoặc planning, tham số `timeout` luôn phải đặt từ `300s` đến `600s`.

## 2. Bài học về Đồng Bộ SQLite SSOT sang Máy Phụ (Remote Host / Admin Cluster)
- **Cạm bẫy đẩy file nhị phân lớn qua PowerShell SSH Chunks:**
  * File SQLite (`farm_master.db`) nặng 1.6MB tương đương 2.17 triệu ký tự Base64.
  * Nếu dùng vòng lặp gửi từng chunk 2.500 ký tự qua mỗi lệnh PowerShell SSH riêng lẻ ($869$ lệnh $\times 3\text{s} = 43.5$ phút), lệnh terminal sẽ bị timeout (300s-600s) ngắt ngang, để lại file SQLite cụt đầu cụt đuôi (`malformed database disk image`).
  * Việc ngụy biện lỗi này do "rớt mạng" hay "lag LAN" là hoàn toàn sai trái; nguyên nhân thực sự là do thiết kế truyền file không đúng quy mô.
- **Giải pháp chuyển giao đúng quy chuẩn:**
  1. **Giải pháp 1 (Local Compilation / In-place Build):** Chạy script `migrate_excel_to_sqlite.py --apply` trực tiếp trên máy phụ (Admin) để nó tự đọc các workbook nguồn đã được OneDrive sync sẵn sang ổ local và biên dịch thành `farm_master.db` chuẩn trong 3 giây.
  2. **Giải pháp 2 (Fallback An Toàn):** Trong các runner đọc SQLite (`run_batch_live_2fa.py`), bắt buộc bọc `try/except (sqlite3.Error, OSError, WorkbookError)` quanh hàm `freeze_targets_from_sqlite()`. Nếu file SQLite chưa toàn vẹn, runner phải tự động fallback êm ái sang freeze targets từ workbook thay vì văng crash làm tê liệt toàn bộ ca chạy.
