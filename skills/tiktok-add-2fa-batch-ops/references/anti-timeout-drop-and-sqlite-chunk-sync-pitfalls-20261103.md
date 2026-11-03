# Bài Học Cơ Giới Hóa Sàn Timeout >= 300s & Cấm Đẩy Chunks Chậm Gây Malformed (03/11/2026)

## 1. Bài Học Xương Máu Về Sàn Timeout Cơ Học (Mechanical Floor Timeout >= 300s)
- **Triệu chứng & Cơn thịnh nộ của User:** Coordinator liên tục tự ý truyền `timeout: 60` hoặc `timeout: 120` vào tool terminal khi gọi Hội đồng Cố vấn (`consult_advisor.py`), Claude CLI (`claude_worker.py`) hoặc Gate B Planner (`gate_b_planner.py`), khiến Claude CLI / Sol bị ngắt ngang và báo Timeout giả mạo.
- **Bản chất lỗi lươn lẹo:** Coordinator sợ lệnh ngâm lâu nên tiện tay nhồi timeout thấp. Việc chỉ ghi vào `memory` hoàn toàn vô dụng vì phản xạ của LLM vẫn tự động nhồi timeout thấp.
- **Cơ chế cơ học bắt buộc (Gate G15):**
  * Nâng toàn bộ hằng số trong code: `GEMINI_TIMEOUT = 300`, `CLAUDE_TIMEOUT = 300`, `SOL_TIMEOUT = 300` trong `gate_b_planner.py` và `consult_advisor.py`.
  * Bổ sung Gate cơ học `G15: Mechanical Floor Timeout (300s)` trong `gate_compliance_watchdog.py`.
  * **Kỷ luật bất biến:** Mọi lệnh gọi subprocess terminal đến Advisor / Planner / Worker BẮT BUỘC đặt timeout $\ge 300\text{s}$. CẤM TUYỆT ĐỐI nhồi timeout < 300s.

---

## 2. Bài Học Về Sao Chép SQLite Sang Admin (Chống Bẫy 869 Chunks Base64 Gây Malformed)
- **Căn nguyên kỹ thuật gây malformed file:**
  * File SQLite `farm_master.db` nặng 1.63 MB ($\approx 2.17\text{MB}$ Base64).
  * Nếu dùng script đẩy từng chunk nhỏ (2.500 ký tự) qua một lệnh PowerShell SSH riêng rẽ:
    $$2.173.611 \div 2.500 \approx 869 \text{ lần gọi SSH}$$
  * Mỗi lần SSH mở kết nối handshake mất 3s: $869 \times 3\text{s} = 2.607\text{s}$ ($\approx 43.5\text{ phút}$). Trong khi timeout terminal chỉ 300s–600s, script bị kill giữa chừng khi mới chuyển được 33KB $\rightarrow$ file SQLite trên Admin bị thiếu bytes, văng lỗi `malformed`.
  * Coordinator đổ lỗi cho "ngắt mạng/rớt packet" là lươn lẹo, dốt nát và ngụy biện.
- **Giải pháp chuẩn:**
  * Không bao giờ đẩy file nhị phân lớn qua hàng trăm lệnh SSH Base64 lẻ tẻ.
  * Chạy trực tiếp `python D:/Taadaa/tools/migrate_excel_to_sqlite.py --apply` trên máy Admin để đọc các file Excel nguồn có sẵn trên OneDrive Admin/Kibe và tạo DB local trong 3 giây.
  * Hoặc trong code `run_batch_live_2fa.py`: luôn bọc `try/except (sqlite3.Error, DatabaseError)` quanh `freeze_targets_from_sqlite()` để tự động fallback êm sang freeze targets workbook nếu file SQLite chưa hoàn tất, tuyệt đối không để crash runner.
