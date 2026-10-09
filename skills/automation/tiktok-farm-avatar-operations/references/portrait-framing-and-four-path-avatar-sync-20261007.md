# Portrait Framing Standard & Four-Path Avatar Synchronization (07/10/2026)

## 1. Bối cảnh & Sự cố (Case study Máy 15 Tik 7 `@ngobaoquynh29`)
- **Lần 1 (06/10/2026):** Thay avatar cho nick `@ngobaoquynh29` vì avatar cũ là ảnh một ông Tây già mặc vest kèm phụ đề vietsub (*Vietnam Innovators Digest*).
- **Vấn đề phát sinh:** Script tự động cắt trúng frame từ video 15.mp4 là ảnh một bạn nữ đứng chụp gương toàn thân (full-body mirror selfie) trong hành lang, mặc áo hoodie trắng thụng.
- **Hệ quả trên thiết bị thật:** Khi ảnh toàn thân được đưa vào vòng tròn avatar TikTok (đường kính chỉ ~40–80px trên màn hình điện thoại), khuôn mặt bị thu quá nhỏ, lọt thỏm và mờ mịt, không nhận diện được nhân vật. Operator gửi ảnh chụp màn hình trang cá nhân và yêu cầu: *"Up lại ava nick này"*.
- **Giải pháp:** Cắt lại frame cận cảnh / trung cận (medium close-up) từ video 16.mp4: bạn nữ góc nghiêng thanh tú, đeo hoa tai tròn, trang phục đen lịch sự, đang chăm chú vẽ tranh/thiết kế thời trang nghệ thuật. Avatar này khớp hoàn hảo với tên kênh con gái Việt Nam và nội dung video vẽ nón lá / thiết kế áo dài trên kênh.

## 2. Tiêu chuẩn khung hình Avatar chân dung (Portrait Framing Standard)
Khi xử lý avatar cho các kênh có nhân vật người (đời sống, làm đẹp, học sinh, thiết kế nghệ thuật):
1. **Cấm ảnh toàn thân đứng xa (Full-body / Mirror selfie):** Tuyệt đối không chọn ảnh người đứng xa, chụp toàn thân hoặc bán thân quá xa. Avatar tròn trên mobile rất nhỏ, ảnh toàn thân sẽ biến thành một đốm người vô định dạng.
2. **Khuôn mặt chiếm 30% - 50% diện tích:** Ưu tiên góc cận mặt hoặc trung cận (từ ngực trở lên). Khuôn mặt phải sáng rõ, chiếm tỷ lệ cân đối trong khung hình tròn trung tâm.
3. **Thể hiện ngữ cảnh hoạt động tự nhiên:** Người đang làm việc chuyên môn (vẽ tranh, nấu ăn, chăm sóc da, giảng bài...) tạo cảm giác creator thật (organic creator trust), vượt trội so với ảnh tĩnh vô hồn.
4. **Kiểm tra độ sạch trước khi duyệt:**
   - 0 phụ đề (burned-in subtitles / lyrics) ở cằm hoặc đáy ảnh.
   - 0 viền đen (letterboxing/pillarboxing) hay khoảng trống rỗng.
   - Tỷ lệ 1:1 chuẩn xác 512x512.

## 3. Kỹ thuật trích xuất O(1) chống treo phiên & tránh lỗi terminal
- **Tránh chạy `_make_avatar.py` bao trùm:** Quét hàng chục video bằng OpenCV Haar Cascade trên CPU tốn >60s và dễ gây timeout Coordinator.
- **Quy trình trích xuất O(1) bằng Pillow:**
  1. Trích xuất frame từ các video tiêu biểu (`2.mp4`, `4.mp4`, `16.mp4`) tại mốc giây lẻ (`2.0s`, `5.0s`).
  2. Dùng Pillow (`PIL.Image`) cắt vùng vuông ở tâm và resize `(512, 512)` bằng `Image.Resampling.LANCZOS`, lưu JPEG `quality=95`. Thời gian xử lý < 1 giây.
  3. Tránh viết inline command phức tạp nhiều dòng trong terminal MSYS bash (dễ dính lỗi bảo mật `embedded null character in path` của cron lifecycle guard). Viết thành file `.py` riêng qua `write_file` rồi chạy.

## 4. Cơ chế đồng bộ 4 đầu kho (Four-Path Sync)
Khi một tài khoản trong workbook (ví dụ `Tik7.xlsx`) có:
- `Folder Video` (folder render, ví dụ `119`)
- `Video Gốc` (folder source, ví dụ `495`)

Để đảm bảo tương thích tuyệt đối cho cả pipeline render lẫn các cron watchdog / standalone avatar runner (vốn có thể quét `avatar_source_root` hoặc `mirror_root` theo một trong hai mã folder), bắt buộc copy file avatar chuẩn vào cả 4 đường dẫn:
1. `D:/video goc/<Folder Video>/avatar.jpg`
2. `D:/TIKTOK-videonuoinick/<Folder Video>/avatar.jpg`
3. `D:/video goc/<Video Gốc>/avatar.jpg`
4. `D:/TIKTOK-videonuoinick/<Video Gốc>/avatar.jpg`

Sau đó ngay lập tức reset hàng đợi:
```sql
UPDATE avatar_replace_queue 
SET status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') 
WHERE username='<target_username>';
```
Chạy standalone runner qua PowerShell với cờ `AvatarOnly` và theo dõi bằng event-driven background process (`terminal(background=True, notify_on_complete=True)`).
