# Avatar Profile Pencil UI & Upload Hook Patterns

## 1. Proxy Password URL-Encoding
Nếu proxy password chứa ký tự đặc biệt như `#`, `!` (ví dụ `TaadaaMobi#2026!`):
- Bắt buộc phải URL-encode bằng `urllib.parse.quote(pwd, safe="")` -> `TaadaaMobi%232026%21`.
- Nếu để raw chuỗi URL `http://user:TaadaaMobi#2026!@host:port`, yt-dlp và curl sẽ parse sai và văng lỗi `407 Proxy Authentication Required` hoặc `Failed to parse`.

## 2. Upload Hook chạy ở phiên cuối ca nuôi (`multi_machine_feed_session.py`)
- **Import path:** Dùng `from python_runner.flows.upload_preflight import ...` với fallback `from flows.upload_preflight import ...` để tránh `ModuleNotFoundError: No module named 'flows'` khi chạy từ repo root.
- **OneDrive File Lock:** File workbook trên `D:\OneDrive\TaadaaData\kibe` hay bị sync lock 1-2s, hàm đọc `openpyxl` bắt buộc bọc retry 3 lần kèm delay `time.sleep(1.5)` để tránh `PermissionError`.
- **Case-insensitive output verification:** Kiểm tra `stdout.lower()` với các biến thể `"post verification passed"`, `"upload video success"`, `"upload completed"`, đồng thời capture `stderr_tail` vào `upload_result.json`.

## 3. TikTok UI Mới - Nút "Sửa hồ sơ" biến mất
- Trên các phiên bản TikTok mới hoặc giao diện profile dạng mới, nút chữ "Sửa hồ sơ" lớn ở giữa bị ẩn, thay vào đó là **biểu tượng cây bút (chỉnh sửa)** nằm ngay bên phải tên hiển thị / username (bounds vùng `[815,205][959,289]`).
- Quy trình cập nhật Avatar qua UI mới:
  1. Tap nút cây bút cạnh tên -> Màn "Sửa hồ sơ".
  2. Tap avatar `[396,552][683,609]` -> Chọn menu "Tải ảnh lên" `[0,1559][1080,1715]`.
  3. Chọn ảnh đầu tiên trong grid "Gần đây" (`/sdcard/Pictures/`) -> Tap "Tiếp (1)" `[780,1788][1044,1896]`.
  4. Màn crop/nhật ký: Bỏ chọn "Đăng ảnh này lên Nhật ký" nếu không cần story -> Tap "Lưu" `[552,1728][1032,1860]`.
  5. Back về màn Profile và xác nhận avatar đã cập nhật.
