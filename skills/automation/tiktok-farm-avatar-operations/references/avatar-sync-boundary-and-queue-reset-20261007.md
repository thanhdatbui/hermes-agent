# Bẫy Phân Định Biên Giới Đồng Bộ Avatar & Cơ Chế Reset Database Cho Watchdog (2026-10-07)

## 1. Bẫy Nghiêm Trọng Khi Đồng Bộ Folder Video vs Video Gốc (Cross-Folder Corruption)

### Hiện tượng
Trong hệ thống Taadaa Phone Farm, một tài khoản vận hành trên 1 máy có cấu trúc mapping:
- `Folder Video` (fv): Thư mục video đã render tại `D:\TIKTOK-videonuoinick\<fv>\` (dùng để đăng và lấy avatar khi upload).
- `Video Gốc` (vg): Thư mục crawl video nguồn gốc tại `D:\video goc\<vg>\` (nội dung thực tế của kênh).

Với công thức chia slot chuẩn (`s` từ 1..8, `m` từ 1..80):
- $fv = (m - 1) \times 8 + s$
- $vg = (s - 1) \times 80 + m$
Có tới hơn 1.200 tài khoản trên toàn farm có $fv \neq vg$.

### Sai lầm chết người (Double Overwrite / Cross-Corruption)
Khi trích xuất avatar đúng từ video gốc `vg`, nếu Coordinator viết script đồng bộ dạng:
```python
# SAI LẦM NGHIÊM TRỌNG:
shutil.copy2(vg_ava, f"D:/TIKTOK-videonuoinick/{fv}/avatar.jpg")  # ĐÚNG
shutil.copy2(vg_ava, f"D:/video goc/{fv}/avatar.jpg")           # CỰC KỲ SAI!
```
**Hậu quả:** Thư mục `D:\video goc\<fv>` KHÔNG PHẢI là đích nhận của tài khoản hiện tại, mà chính là nguồn video gốc của một tài khoản KHÁC (tài khoản có $vg = fv$). Việc copy đè vào `D:\video goc\<fv>` sẽ làm tha hóa (corrupt) avatar của tài khoản khác đó, gây ra dây chuyền sai lệch avatar hàng loạt!

### Quy tắc bất biến
1. Nguồn avatar gốc luôn nằm tại `D:\video goc\<vg>\avatar.jpg`.
2. Đích đến duy nhất cần đồng bộ là thư mục render của runner: `D:\TIKTOK-videonuoinick\<fv>\avatar.jpg`.
3. **CẤM TUYỆT ĐỐI** can thiệp hay ghi đè vào `D:\video goc\<fv>\avatar.jpg` khi $fv \neq vg$.

---

## 2. Cơ Chế Reset Database `avatar_replace_queue` Cho Cron Watchdog

### Vấn đề
Khi chạy công cụ sinh lại avatar độc bản trên ổ đĩa (`_make_avatar.py` hoặc `regenerate_unique_avatars.py`), các file ảnh mới chỉ nằm trên đĩa.
Watchdog upload tự động (`post_evening_avatar_watchdog.py`) truy vấn:
```python
if queue_status == "PENDING":
    unuploaded.append(may)
elif queue_status == "DONE" or has_avatar == 1:
    uploaded_count += 1
```
Nếu các tài khoản đã từng up avatar trong quá khứ và được lưu `status = 'DONE'` trong `avatar_replace_queue` (hoặc `has_avatar == 1` trong snapshot), watchdog sẽ **BỎ QUA HOÀN TOÀN**, không bao giờ upload ảnh mới lên máy thật.

### Quy trình bắt buộc sau khi trích xuất avatar mới
Ngay sau khi tái tạo hoặc thay đổi file avatar trên đĩa, BẮT BUỘC phải thực thi câu lệnh SQL reset hàng đợi:
```sql
UPDATE avatar_replace_queue 
SET status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime')
WHERE status != 'PENDING';
```
Xác nhận read-back kiểm tra số lượng bản ghi `PENDING` khớp với số tài khoản cần cập nhật trên toàn farm trước khi bàn giao ca.

---

## 3. Cơ Chế Chống Trôi Hashtag Do Cron Sync 15 Phút (`sync_all_tik_keywords.py`)

### Hiện tượng
Đã sửa bằng tay hoặc chạy script fix cột `Keyword Video` và `Hashtag Pool` trong file Excel `Tik*.xlsx`, nhưng sau đó kiểm tra lại thấy quay về hashtag sai (ví dụ kênh Khoa học/Khám phá bị biến thành `thucung`).

### Nguyên nhân gốc rễ
Cron job `sync-all-tik-keywords-cron` chạy định kỳ 15 phút. Nguồn chân lý (Source of Truth) của nó là file database SQLite `D:\CodexRuntime\tiktok-video\state.db`, bảng `folders`, cột `niche`.
Nếu trong `state.db` folder đó bị gán nhãn sai (do crawler hoặc phân loại nhầm tên uploader), cron job sẽ liên tục đọc nhãn sai từ DB và ghi đè ngược lại vào tất cả các file Excel!

### Quy trình sửa triệt để
1. Cập nhật `state.db`:
   ```sql
   UPDATE folders SET niche = 'khoahoc' WHERE folder_num = 450;
   UPDATE videos SET niche = 'khoahoc' WHERE folder = 450;
   ```
2. Kích hoạt đồng bộ thủ công để ghi nhận ngay:
   ```bash
   python C:/Users/Kibe/AppData/Local/hermes/scripts/sync_all_tik_keywords.py
   ```
3. Read-back đối soát các file Excel (`Kibe/Tik*.xlsx` và `Admin/Tik*.xlsx`) để xác nhận keyword và hashtag pool đã chuyển sang niche chuẩn.
