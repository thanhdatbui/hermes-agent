# Invariant Sàn Timeout Terminal & Đồng Bộ SQLite Hai Cụm Farm (2026-11-03)

## 1. Hard Invariant: Cấm Nhồi Timeout Thấp (<300s) Vào Terminal
- **Bối cảnh sự cố:** Coordinator có tật xấu tự tiện truyền cờ `timeout=60` hoặc `timeout=120` khi gọi `consult_advisor.py`, `claude_worker.py` hoặc các sub-process. Hậu quả: Claude CLI và các tiến trình suy luận sâu bị runtime kill ngang ở giây 60, làm mất phản biện chéo khách quan của Hội đồng Cố vấn, gây ức chế nghiêm trọng cho User.
- **Quy tắc bất biến:**
  * Mọi lệnh `terminal` khi gọi Hội đồng Cố vấn (`consult_advisor.py`), Claude CLI (`claude_worker.py`), Planner (`gate_b_planner.py`), Pipeline liên hoàn (`unified_patch_pipeline.py`) **BẮT BUỘC PHẢI TRUYỀN TIMEOUT >= 300s** (khuyến nghị 300s - 600s).
  * CẤM TUYỆT ĐỐI tự ý hạ timeout dưới 300s với lý do "tránh ngâm chat".

---

## 2. Kiến Trúc Đồng Bộ SQLite SSOT Giữa Cụm Kibe & Cụm Admin
- **Đặc tính phân vùng vật lý:**
  * Cụm Kibe: Quản lý cố định máy 1–80 (640 accounts).
  * Cụm Admin: Quản lý cố định máy 201–280 (640 accounts).
  * Không có bất kỳ account hay machine nào bị chồng chéo (Zero Data Overlap).
- **Mô hình Vận hành Độc lập + High Availability (HA):**
  * Mỗi máy giữ file SQLite local riêng tại `D:/Taadaa/data/farm_master.db`.
  * Khi Kibe SSH sang Admin để kích hoạt batch, Python trên Admin đọc/ghi trực tiếp file local của Admin với tốc độ O(1) ~ 0.005s, không phụ thuộc vào kết nối mạng hay handle của Kibe.
  * Nếu máy Kibe bị tắt nguồn, hỏng phần cứng hay rớt mạng, máy Admin vẫn hoàn toàn tự chủ vận hành toàn bộ 80 máy của cụm mình.
- **Quy trình đẩy bản dump SQLite sang Admin qua SSH (Tránh bẫy Base64 payload):**
  * File nhị phân `.db` 1.6MB nếu chia chunk thô qua PowerShell Base64 dễ bị timeout hoặc lỗi malformed.
  * Phương pháp chuẩn:
    1. Dump SQL và nén Gzip trên Kibe: `dump_sql = '\n'.join(conn.iterdump()); compressed = gzip.compress(dump_sql, 9)` (giảm từ 1.6MB xuống ~450KB).
    2. Đẩy các chunk Base64 (size <= 2.500 chars) sang `D:/Taadaa/data/farm_master_dump.sql.gz` trên Admin.
    3. Giải nén và nạp trực tiếp qua Python SQLite trên Admin:
       ```python
       import gzip, sqlite3
       data = gzip.decompress(open(r'D:/Taadaa/data/farm_master_dump.sql.gz', 'rb').read()).decode('utf-8')
       conn = sqlite3.connect(r'D:/Taadaa/data/farm_master.db')
       conn.executescript(data)
       conn.close()
       ```
    4. Đối soát số lượng record read-back: 1.270 accounts (630 account Admin), 1.513 mailboxes. Sau đó xóa file `.gz` tạm.
