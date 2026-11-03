# Quy Chuẩn Chặn Cơ Học Sàn Timeout >= 300s & Đồng Bộ SQLite Farm Master (2026-11-03)

## 1. Bài Học Xương Máu Về Sàn Timeout Cơ Học (Mechanical Timeout Floor >= 300s)
- **Triệu chứng & Cơn thịnh nộ của User:** Coordinator tiện tay nhồi tham số `timeout: 60` hoặc `timeout=60` vào lệnh gọi terminal khi chạy `consult_advisor.py`, `claude_worker.py` hoặc `gate_b_planner.py`.
- **Hậu quả:** Claude CLI Sonnet và Sol Web cần thời gian đọc bối cảnh hiện trường, khi bị Coordinator bóp chết ở giây thứ 60, tiến trình bị ngắt ngang và báo `TIMEOUT (>60s)`. Điều này dẫn đến sự cố thiên kiến một chiều (Single-Advisor Bias) hoặc làm hỏng quá trình lập plan.
- **Kỷ luật cưỡng chế (Mechanical Enforcement Gate G15):**
  - CẤM TUYỆT ĐỐI Coordinator truyền bất kỳ timeout nào `< 300s` trong tool `terminal`. MỌI lệnh terminal gọi Advisor Council, Worker, Pipeline, Planner BẮT BUỘC đặt `timeout >= 300`.
  - Gate G15 trong `gate_compliance_watchdog.py` quét regex tự động: phát hiện `(timeout|time_limit|timeout_seconds) < 300` là DENY và đánh cờ vi phạm nghiêm trọng.
  - Các hằng số trong code (`gate_b_planner.py`, `consult_advisor.py`): Khóa cứng `CLAUDE_TIMEOUT = 300`, `GEMINI_TIMEOUT = 300`, `SOL_TIMEOUT = 300`.

## 2. Kiến Trúc Đồng Bộ SQLite farm_master.db Đa Cụm (Kibe vs Admin)
- **Bản chất hạ tầng:**
  - Kibe quản lý máy 1-80 (640 tài khoản).
  - Admin quản lý máy 201-280 (640 tài khoản).
  - Zero Data Overlap: Hai cụm không hề có máy hay tài khoản nào chồng chéo.
- **Nguyên tắc vận hành:**
  - Mỗi máy giữ một bản local tại `D:/Taadaa/data/farm_master.db` để các runner Python trên máy đó đọc/ghi $O(1) \approx 0.005s$.
  - Khi Kibe SSH sang Admin: script trên Admin chạy cục bộ bằng Python Admin, bắt buộc đọc `farm_master.db` local của Admin.
  - Không sync qua OneDrive WAL để tránh kẹt lock.
  - Khi file SQLite trên Admin bị thiếu/malformed trong lúc sync: Runner bắt buộc có try/except bọc ngoài để tự động fallback sang nạp targets từ workbook Admin, đảm bảo không bao giờ làm chết ca chạy của farm.
