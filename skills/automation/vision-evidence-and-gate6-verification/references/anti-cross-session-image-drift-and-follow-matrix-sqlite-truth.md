# Anti-Cross-Session Image Drift & Single Source of Truth for Follow Drops (2026-10-29)

## 1. Context & Incident Summary
1. **Sự cố 1 (Lệch ảnh / Lệch session giữa các chat Telegram)**:
   - Khi chạy đa phiên / song song trên host Windows, Telegram Gateway tải mọi ảnh người dùng gửi vào `%LOCALAPPDATA%\hermes\image_cache\img_<hash>.jpg`.
   - Khi native vision văng lỗi ngầm (vd `No module named 'agent.aux_accounting'`), Agent fallback sang WinRT OCR nhưng lại viết script Python quét mò:
     `sorted(glob("%LOCALAPPDATA%/hermes/image_cache/*"), key=os.path.getmtime)[0]`
   - Do có luồng chạy ngầm khác (vd xử lý xác minh Google account qua GPM) vừa tải một ảnh QR về cache, Agent bốc nhầm ảnh QR của luồng đó và trả lời sai hoàn toàn ngữ cảnh của User.

2. **Sự cố 2 (Mất lịch sử ca nhả follow khi `fail_streak > 1`)**:
   - Tài khoản có `fail_streak = 3`, nhưng Sổ bệnh án (popup modal trên Web Dashboard 1905) chỉ hiện 1 ca nhả gần nhất.
   - Nguyên nhân: File state JSON (`follow_state_<machine>_row_<row>.json`) chỉ lưu 1 biến `last_failed_date`, lần fail sau ghi đè lần fail trước. Các ca fail trước đó không có follow nào (`followed_count = 0`), nên danh sách `followed` không có bản ghi UID nào trong ngày đó.
   - Khi Claude CLI thẩm định độc lập: cảnh báo rủi ro "Hai nguồn sự thật" (Split-Brain Truth) nếu chỉ dựa vào mảng `drop_history` trong file state JSON. Cơ sở dữ liệu SQLite (`daily_account_actions` trong `D:/Taadaa/data/tiktok_tracker.db`) mới là nguồn sự thật duy nhất ghi nhận mọi phiên chạy trong lịch sử.

---

## 2. Hard Invariants & Implementation Fixes

### A. Cơ giới hóa chống đoán mò ảnh (Anti-Image-Drift Invariant)
1. **CẤM TUYỆT ĐỐI**:
   - Cấm dùng `glob`, `getmtime`, `getctime`, `os.stat`, `ls -t` hay `sorted()` để nhặt "file ảnh mới nhất" trong `image_cache`.
2. **Quy tắc neo đích danh (Exact Hash Anchor)**:
   - Bắt buộc trích xuất đích danh file hash xuất hiện trong prompt của User:
     `[Image attached at: ...\img_<exact_hash>.jpg]`.
   - Nếu file không tồn tại hoặc lỗi, FAIL-CLOSED báo lỗi ngay lập tức, cấm tự ý quét thư mục để nhặt file khác thay thế.
3. **Chuẩn hóa đường dẫn WinRT OCR**:
   - `Windows.Storage.StorageFile::GetFileFromPathAsync` văng `AggregateException` nếu path chứa dấu `/`.
   - Runner OCR (`run_ocr.py`) bắt buộc chuẩn hóa:
     ```python
     target_img = os.path.abspath(target_img).replace('/', '\\')
     ```

### B. Single Source of Truth cho Ma trận Sổ bệnh án
1. **Lấy SQLite làm nguồn sự thật cho lịch sử ca chạy**:
   - Thay vì chỉ dựa vào `followed` trong JSON, hàm `get_account_follow_detail` trong `follow_health_helper.py` kết nối trực tiếp SQLite:
     ```python
     if username and username != "-" and os.path.exists(db_path):
         try:
             with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0) as conn:
                 cur = conn.cursor()
                 cur.execute(
                     "SELECT target_date, internal_follows FROM daily_account_actions WHERE username = ? COLLATE NOCASE",
                     (username,),
                 )
                 for t_date, cnt in cur.fetchall():
                     if t_date:
                         t_str = str(t_date)
                         c_val = int(cnt or 0)
                         if t_str not in daily:
                             daily[t_str] = c_val
                         if c_val == 0:
                             drop_dates.add(t_str)
         except Exception as e:
             logger.debug("could not load daily_account_actions: %s", e)
     ```
   - Mọi ca chạy có `internal_follows == 0` được đánh dấu là `is_drop = True`, tái hiện trọn vẹn toàn bộ các ca fail trong quá khứ ngay trên Sổ bệnh án.
