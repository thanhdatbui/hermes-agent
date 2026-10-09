# MISMATCH_GOC Drift and Watchdog Tik Exclusion Triage (2026-10-10)

## 1. Bối cảnh sự cố & Lỗi ngộ nhận "Đã đánh dấu hết"
Trong các phiên trước (04/10 – 07/10/2026), Coordinator từng báo cáo với Operator rằng:
- "Đã tạo lại avatar độc bản và cập nhật toàn bộ cờ PENDING cho toàn farm".
- "Watchdog ca tối đã cày cuốn chiếu và chỉ còn vài chục acc lẻ".

Tuy nhiên, khi Operator kiểm tra kênh `@dongoc2504` (Máy 26 Tik 2 Kibe) ngày 10/10/2026:
- Kênh vẫn mang avatar trùm lưới trang điểm cũ (@tipmakeupeasy) từ tháng 7/2026.
- Bảng `avatar_replace_queue` trong `tiktok_tracker.db` vẫn ghi nhận:
  `('dongoc2504', 26, 2, 'kibe', '202', '106', 'PENDING', 'MISMATCH_GOC (diff=70.4)', '2026-10-02 16:28:45')`.

## 2. Căn nguyên hệ thống 2 tầng
Khi kiểm toán toàn bộ bảng `avatar_replace_queue`:
1. **140 tài khoản bị kẹt `MISMATCH_GOC` tồn đọng từ 02/10/2026**:
   - `kibe`, Tik 1: 73 tài khoản.
   - `kibe`, Tik 2: 67 tài khoản.
   - Toàn bộ 140 tài khoản này đều bị dính cờ `MISMATCH_GOC` do công thức kép:
     `Folder Video = (Máy - 1) * 8 + Tik` (chia theo máy) vs `video gốc = (Tik - 1) * 80 + Máy` (chia theo ca).
     Khi kiểm tra đối soát thấy 2 folder khác số, script cũ đã gán nhãn `MISMATCH_GOC` và dừng lại.
2. **Watchdog ca tối (`post_evening_avatar_watchdog.py`) loại trừ hoàn toàn Tik 1 & Tik 2 Kibe**:
   - Cấu hình cluster Kibe trong script:
     ```python
     cluster_order = [
         ("kibe", "FARM KIBE - MÁY 1-80", [5, 6, 7, 8, 3, 4]),
         ("admin", "FARM ADMIN - MÁY 201-280", [1, 2, 3, 4, 5, 6, 7, 8]),
     ]
     ```
   - Ca tối chỉ quét các Tik `[5, 6, 7, 8, 3, 4]`. Do đó, Tik 1 và Tik 2 của Kibe KHÔNG BAO GIỜ được watchdog ca tối bốc chạy, khiến 140 nick này bị bỏ quên vĩnh viễn dù file trên đĩa đã từng được quét.

## 3. Kỹ thuật Grid-Assisted Circular Avatar Crop
Khi trích xuất avatar chân dung từ video TikTok dọc (1080x1920):
1. **Lỗi crop mò**: Thường cắt trúng người đứng cạnh, bị cắt cụt đỉnh tóc (headroom âm), hoặc mắt bị dồn xuống đáy hình tròn TikTok.
2. **Quy trình chuẩn hóa 3 bước**:
   - Bước 1: Vẽ lưới tọa độ xanh (`draw_grid.py`) lên frame sắc nét nhất của video, gọi Vision API đọc chính xác tọa độ: Đỉnh tóc, Mắt trái/phải, Cằm, Biên trái/phải của khuôn mặt.
   - Bước 2: Tính tâm `cx = (x_left + x_right) / 2`, `cy = (y_top + y_chin) / 2`. Chọn `side = (y_chin - y_top) * 1.25..1.35` để mặt chiếm 50-60% diện tích, đường mắt nằm ở 1/3 trên của hình tròn.
   - Bước 3: Mô phỏng circular mask (`cv2.circle(mask)` + nền trắng) và gọi Vision chấm điểm. Chỉ dùng ảnh khi đạt điểm $\ge 8.0/10$ (như Chu Dực Nhiên đạt 8.5/10).

## 4. Quy trình khắc phục dứt điểm cho 140 acc MISMATCH_GOC
1. **Đồng bộ Workbook & SQLite**:
   - Khóa cứng `video gốc = Folder Video` trong `Tik1.xlsx` và `Tik2.xlsx`.
   - Chạy lệnh SQL:
     ```sql
     UPDATE avatar_replace_queue
     SET video_goc = folder_video, status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime')
     WHERE last_error LIKE 'MISMATCH_GOC%';
     ```
2. **Chạy runner độc lập cho Tik 1 & Tik 2 Kibe**:
   - Không thụ động chờ watchdog ca tối.
   - Khởi chạy runner PowerShell chỉ định riêng Tik 1 và Tik 2 theo từng mẻ máy rảnh.
