# Video Posted Count Reset & Overwritten Source Niche Clash (2026-10-09)

## Context & Incident Case Study
Khi Operator gửi ảnh Profile TikTok của tài khoản `@yuethutiubk` (Máy 62 / Tik 8 / tên "Hoàng Khoa") thắc mắc:
*"Đổi ava nick này. Mà sao đoạn trc đăng gái còn vidoe ms nhất lại là giao thông v"*

Profile ghi nhận hiện trạng dị thường:
- Avatar: Hình tròn nền vàng với chữ in đậm màu đen **"hôi"**.
- Lưới video (8 clips):
  - Row 1 (3 clips mới nhất): Camera giao thông / dashcam tai nạn xe (*"Chịu thua!", "KHÔNG LÀM GÌ ĐƯỢC...", "Tạt cánh - đâm đầu"*).
  - Row 2 & Row 3 (5 clips cũ hơn): Bạn nữ trẻ đeo kính tròn, áo jersey #4, đời sống/agency vlog (*"Pov: Tui khi làm ở agency"*).
- Excel `Tik8.xlsx`: `Keyword Video = Kinh doanh`, `Folder Video = 496`, `video gốc = 622`, `Video Đã Đăng = 3`.

## Chuỗi Nguyên Nhân Kép Gây Ra Lỗi (Root Cause Analysis)

1. **Đè nguồn thư mục Render (`Folder Video`):**
   - Tài khoản được đăng ký ngày 25/08/2026, từ cuối tháng 8 đến 20/09 đã đăng 5 clip bạn nữ vlog/agency.
   - Ngày 11/09/2026, thư mục nguồn `D:\video goc\496` bị tải đè kênh YouTube `@Cameragiaothong`. Ngày 16/09/2026, tool render xuất 46 video tai nạn giao thông vào `D:\TIKTOK-videonuoinick\496`.

2. **Bẫy reset `Video Đã Đăng` về 0 trong Workbook:**
   - Trong bản backup workbook `Tik8.backup_20260927_222329.xlsx`, cột `Video Đã Đăng` của Máy 62 bị để giá trị `0` (thay vì ghi nhận đúng số lượng `5` clip đã có trên kênh).
   - Khi runner upload batch chạy cho Tik 8, công thức khởi tạo là:
     $$\text{start\_seq} = \text{Video Đã Đăng} + 1 = 0 + 1 = 1$$
   - Bot bốc từ `1.mp4`, `2.mp4`, `3.mp4` trong folder 496 (vốn là video giao thông vừa render) để upload lên kênh vào các ngày 30/09, 06/10 và 08/10. Hệ quả: kênh bị rách tệp nghiêm trọng (5 clip gái xinh bị nối tiếp bởi 3 clip tai nạn xe).

3. **Cơ chế Watchdog cắt nhầm avatar chữ "hôi":**
   - Ngày 07/10/2026, watchdog avatar (`post_evening_avatar_watchdog.py`) thấy tài khoản trong `avatar_replace_queue` có `Folder Video = 496`.
   - Tool `_make_avatar.py` tự động cắt frame từ `1.mp4` của folder 496. Clip này mở đầu bằng banner cảnh báo tai nạn màu vàng có chữ *"thôi"*. Thuật toán phát hiện box crop lẹm mất chữ 't' $\to$ thành chữ **"hôi"** màu vàng, rồi watchdog tự upload đè lên tài khoản TikTok.

## Quy Trình Chẩn Đoán O(1) Đối Soát 3 Tầng (Không Quét Đĩa)

1. **Tầng 1 — Lịch sử số lượng video và avatar trong SQLite (`snapshots`):**
   ```sql
   SELECT timestamp, video, avatar_thumb, created_at 
   FROM snapshots 
   WHERE username = 'yuethutiubk' 
   ORDER BY id ASC;
   ```
   - Xác định chính xác ngày kênh có 4, 5 clips (trước 20/09) và ngày tăng lên 6, 7, 8 clips (30/09, 06/10, 08/10).
   - Xác định thời điểm avatar bị thay đổi (`avatar_thumb` đổi URL lúc 11:07 ngày 07/10/2026).

2. **Tầng 2 — Đối soát lịch sử workbook qua các bản backup:**
   - Đọc hàng máy trong các file backup `Tik<N>.backup_*.xlsx`, `.bak`, `taikhoan_run_safe.xlsx` để phát hiện thời điểm `Video Đã Đăng` bị reset về 0.

3. **Tầng 3 — Đối soát mtime file và Global Ledger:**
   - Kiểm tra mtime của `1.mp4` trong `video goc` và `TIKTOK-videonuoinick`.
   - Tra cứu `global-ledger/*.jsonl` theo số folder để xác định đúng URL kênh YouTube/TikTok đã tải về folder đó vào thời gian nào.

## Quy Trình Cứu Vãn & Tạo Avatar Composite Khi File Nguồn Cũ Bị Ghi Đè

Khi các file video cũ của kênh đã bị xóa hoặc ghi đè trên ổ cứng:
1. **Trích xuất chân dung từ Profile Screenshot:**
   - Dùng Pillow crop trực tiếp từ thumbnail của các video cũ trên ảnh chụp màn hình Profile do Operator cung cấp (`x, y, w, h` theo tọa độ lưới 3 cột).
   - Chọn các thumbnail chân dung cận cảnh (selfie, góc mặt rõ nét) thay vì góc toàn thân hoặc có biểu tượng play che khuất.
   - Upscale lên chuẩn vuông 512x512 bằng `Image.Resampling.LANCZOS` và lưu JPEG quality 95.

2. **Dựng Canvas Composite 4 Panel kèm Circular Mask:**
   - Dùng Pillow vẽ mask tròn đường kính 300px đối chiếu: Panel 1 (Ava lỗi hiện tại) vs Panel 2, 3, 4 (Các options chân dung bạn nữ).
   - Đính kèm hộp giải trình ngắn gọn 4 gạch đầu dòng nguyên nhân kỹ thuật ở chân ảnh.

3. **Soi mắt kiểm tra trước qua 9Router Vision API:**
   - Gửi ảnh qua `http://127.0.0.1:20128/v1/chat/completions` (model `ag/gemini-3.7-flash-high`, stream: False).
   - Xác nhận: 4 panel hiển thị đủ, mask tròn sắc nét, không bị lẹm mặt, không đen màn hình trước khi gửi thẻ `MEDIA:`.

4. **Biện pháp ngăn ngừa & Chặn bot đăng tiếp:**
   - Cập nhật ngay cột `Video Đã Đăng = 8` trong `Tik<N>.xlsx` để bot không bốc tiếp các clip giao thông còn lại trong folder.
   - Hoán đổi nguồn (Source Swap) đưa folder 496 về đúng ngách nội dung gốc hoặc Niche Hot trước khi mở lại ca đăng video.
