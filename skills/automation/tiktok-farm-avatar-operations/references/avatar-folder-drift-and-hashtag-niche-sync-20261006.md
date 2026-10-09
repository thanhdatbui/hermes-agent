# Case Study: Lệch Folder Video vs Video Gốc & Bẫy Hashtag Drift Qua Cron Watchdog (2026-10-06)

## 1. Hiện Trường Sự Cố (Tài khoản `@maigiangan09` - Máy 50 Tik 6)
- **Tài khoản**: `@maigiangan09` (Máy 50 - Slot Tik 6 trên cụm Kibe).
- **Hiện tượng 1 (Avatar bậy)**: Profile đăng toàn bộ video về khoa học / khám phá / bí ẩn lịch sử (voi ma mút, xác ướp, xương rồng, vũ trụ), nhưng avatar trên máy lại là ảnh một bạn nữ selfie làm đẹp / trang điểm.
- **Hiện tượng 2 (Hashtag sai)**: Mặc dù đã quét sửa hashtag hàng loạt trước đó, trên profile các video đăng mới vẫn gắn hashtag `#thucung #chamsocthucung ...`.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### A. Bẫy Lệch Mapping `Folder Video` (398) $\neq$ `Video Gốc` (450)
1. Trong file workbook (`D:\OneDrive\TaadaaData\kibe\Tik6.xlsx`):
   - Cột `Folder Video`: `398` (thư mục video render để up bài).
   - Cột `video gốc`: `450` (thư mục crawl nguồn từ YouTube `@qndiscovery23` - QN TV Discovery).
2. Khi runner `resolve_avatar_path` tìm avatar để upload:
   - Logic tìm file ưu tiên: `D:\video goc\<Folder Video>\avatar.jpg` và fallback `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`.
   - Vì `Folder Video` = 398, runner đọc thư mục **398**.
   - Thư mục 398 nguyên thủy là niche **Trang điểm / Làm đẹp** (`@ĐẹplàBeauty-l1k`), chứa file `avatar.jpg` là ảnh gái làm đẹp!
3. Khi đợt quét tạo avatar mới tự động chạy:
   - Script sinh ảnh mới theo danh mục `video gốc` (folder 450) $\rightarrow$ sinh ra ảnh thanh niên áo vàng đứng trước voi ma mút trong `D:\video goc\450\avatar.jpg`.
   - Do không copy đồng bộ sang folder 398, thư mục 398 vẫn giữ avatar trang điểm cũ.

### B. Bẫy Kẹt Cờ `DONE` Trong `avatar_replace_queue`
- Trong SQLite `D:/Taadaa/data/tiktok_tracker.db`, bảng `avatar_replace_queue`, nick `@maigiangan09` đã được lưu `status = 'DONE'` từ ngày **03/10/2026 05:17:18**.
- Cron watchdog buổi tối (`post_evening_avatar_watchdog.py`) kiểm tra:
  * Nếu nick đã có avatar (`has_avatar == 1`) VÀ trạng thái trong queue là `DONE` $\rightarrow$ BỎ QUA HOÀN TOÀN.
  * Vì vậy, dù trên đĩa đã sinh avatar mới vào đêm 04/10, máy 50 không bao giờ được bốc lên để chạy đè.

### C. Bẫy Regex False Positive & Cơ Chế Đè Của Cron 15 Phút
1. Kênh `@qndiscovery23` tải về folder 450 có uploader metadata là `Mèo Cam TV`.
2. Script phân loại tự động dùng regex:
   `any(k in name for k in ['yeulu', 'mèo', 'chó', 'pet', 'thú cưng', ...])`
   $\rightarrow$ Bắt trúng chữ `mèo` trong tên "Mèo Cam TV" $\rightarrow$ gán nhầm `niche = 'thucung'` trong `state.db`.
3. Cron watchdog `sync_all_tik_keywords.py` chạy mỗi 15 phút:
   - Đọc `state.db` thấy folder 450 mang nhãn `thucung`.
   - Tự động ghi đè cột `Keyword Video = 'Thú cưng'` và `Hashtag Pool = '#thucung ...'` vào `Tik6.xlsx` Máy 50!
   - Vì vậy, nếu chỉ sửa trên Excel mà không sửa trong `state.db`, sau 15 phút cron sẽ ghi đè lại hashtag thú cưng.

---

## 3. Quy Trình Khắc Phục Chuẩn Hóa
1. **Sửa tại nguồn chân lý `state.db` trước**:
   ```python
   conn = sqlite3.connect(r"D:\CodexRuntime\tiktok-video\state.db")
   conn.execute("UPDATE folders SET niche = 'khoahoc' WHERE folder_num = 450")
   conn.execute("UPDATE videos SET niche = 'khoahoc' WHERE folder = 450")
   conn.commit()
   ```
2. **Kích hoạt sync nguyên tử sang Excel cho cả 2 cụm (Kibe & Admin)**:
   ```bash
   python C:/Users/Kibe/AppData/Local/hermes/scripts/sync_all_tik_keywords.py
   ```
3. **Đồng bộ avatar sang đúng `Folder Video` ở cả 2 đầu kho**:
   - Copy `D:\video goc\450\avatar.jpg` $\rightarrow$ `D:\video goc\398\avatar.jpg`
   - Copy `D:\video goc\450\avatar.jpg` $\rightarrow$ `D:\TIKTOK-videonuoinick\398\avatar.jpg`
4. **Reset trạng thái hàng đợi `avatar_replace_queue`**:
   ```sql
   UPDATE avatar_replace_queue 
   SET status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime') 
   WHERE username = 'maigiangan09';
   ```
5. **Soi mắt qua Vision API trước khi xác nhận**:
   - Sử dụng Direct Vision API (hoặc WinRT OCR) kiểm tra ảnh nguồn: Đúng chủ đề khoa học/voi ma mút, không còn avatar gái xinh.
