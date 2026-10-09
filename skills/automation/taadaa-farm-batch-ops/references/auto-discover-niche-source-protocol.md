# Auto-Discover Niche Source Protocol (download_by_niche.py)

Tài liệu chuẩn hóa kiến trúc và quy chuẩn code review cho cơ chế `auto_discover_niche_source` trong script `D:\Taadaa\Tiktok-video\scripts\download_by_niche.py`.

## 1. Nguyên tắc cốt lõi (Code Review Gate)

### A. An toàn trích xuất dữ liệu yt-dlp
Khi dùng yt-dlp `extract_info` ở chế độ `flat=True`:
- `res` có thể là `None` hoặc kiểu không phải `dict` nếu truy vấn không trả về kết quả.
- `res.get("entries")` có thể là `None` hoặc chứa các entry không phải `dict`.
- **Bắt buộc**:
  ```python
  res = ydl.extract_info(q, download=False)
  if not isinstance(res, dict):
      continue
  for e in res.get("entries") or []:
      if not isinstance(e, dict):
          continue
  ```

### B. Chuẩn hóa URL qua `source_key`
Không dùng `url.lower().rstrip("/")` đơn thuần để so khớp, vì YouTube có thể biểu diễn cùng một kênh qua `@handle`, `/channel/UC...`, hoặc `/c/...`.
- Dùng `source_key(norm_url)` thống nhất:
  - Khởi tạo: `existing_keys = {source_key(s.url) for s in sources}`
  - Kiểm tra ledger: `source_key(norm_url) not in claimed_keys`
  - So sánh trong file JSON: `not any(source_key(s.get("url", "")) == source_key(ch_url) for s in raw_sources)`

### C. Thứ tự Transactional Claim Ledger vs File Write
Để tránh ghi rác vào file cấu hình dùng chung `sources.qualified30.json` hoặc xung đột giữa các tiến trình/máy:
1. **Khóa DB**: Toàn bộ quy trình chạy trong `with _DB_LOCK:`.
2. **Re-check**: Kiểm tra lại `source_key(ch_url)` trong `sources` và ledger hiện tại.
3. **Claim Ledger TRƯỚC**:
   ```python
   if not claim_source(getattr(args, "global_ledger_dir", None), machine_id, ch_url, folder_num):
       continue
   ```
4. **Ghi Atomic vào sources JSON**: Sau khi claim thành công, ghi append vào `sources_file` bằng cơ chế ghi file tạm rồi `os.replace`.
5. **Ghi SQLite `state.db`**: Gọi `insert_discovered(conn, c)` và `conn.commit()`.
6. **Mutate in-memory**: Cập nhật `temp_source` và `sources.append(temp_source)`.

## 2. Lệnh kiểm tra và xác minh (Verification)
Sau khi chỉnh sửa `download_by_niche.py`, luôn chạy cú pháp compile bằng virtualenv chuyên biệt:
```bash
D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -m py_compile D:/Taadaa/Tiktok-video/scripts/download_by_niche.py
```
Exit code 0 đảm bảo không lỗi cú pháp hoặc thụt lề.
