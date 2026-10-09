# Overwritten Source Reversion and Grid Avatar Recovery (2026-10-09)

## 1. Context & Incident
Tài khoản `@yuethutiubk` (Máy 62 / Tik 8, tên hiển thị "Hoàng Khoa"):
- **Hiện tượng:** Operator gửi ảnh profile và thắc mắc: *"Đổi ava nick này. Mà sao đoạn trc đăng gái còn video ms nhất lại là giao thông v"*. Avatar hiện tại là một hình tròn màu vàng có chữ đen cụt lủn **"hôi"**.
- **Lưới video trên Profile:**
  - Row 2 & 3 (5 video cũ): Bạn nữ trẻ đeo kính gọng tròn, mặc áo agency, áo thể thao Nike Alabama #4, clip concert (view đạt tới 765 view).
  - Row 1 (3 video mới nhất): Clip camera hành trình tai nạn giao thông (view flop nặng ở mức 48 view).

## 2. Chuỗi Nguyên Nhân Cốt Lõi (Root Cause Chain)
1. **Ghi đè nguồn không kiểm soát (Uncoordinated Crawl Overwrite):**
   - Thư mục nguồn `D:\video goc\496` ngày 11/09 bị tải đè kênh YouTube `@Cameragiaothong`.
   - Ngày 16/09, tool render xuất 46 clip tai nạn giao thông vào `D:\TIKTOK-videonuoinick\496`. Toàn bộ file mp4 của bạn nữ agency cũ bị xóa sổ khỏi ổ đĩa.
2. **Reset sai bộ đếm `Video Đã Đăng` trong Excel:**
   - Trong `Tik8.xlsx`, hàng Máy 62 gán `Folder Video: 496`, nhưng cột `Video Đã Đăng` bị reset về `0` (thay vì ghi nhận đúng `5` clip đã có trên kênh).
   - Bot upload tính `start_seq = Video Đã Đăng + 1 = 1`, dẫn tới việc bot bốc các clip `1.mp4`, `2.mp4`, `3.mp4` trong folder 496 (tai nạn đường phố: *Chịu thua!, Không làm gì được, Tạt cánh đâm đầu*) để đăng lên nick vào cuối tháng 9 và đầu tháng 10.
3. **Watchdog avatar cắt nhầm chữ banner tai nạn:**
   - Ca tối ngày 07/10/2026, watchdog avatar (`post_evening_avatar_watchdog.py`) thấy nick có `Folder Video: 496`.
   - Tool `_make_avatar.py` tự động cắt frame từ `1.mp4` của folder 496. Clip này mở đầu bằng banner cảnh báo tai nạn màu vàng chữ *"thôi"*, tool cắt lẹm mất chữ 't' $\to$ thành chữ **"hôi"** màu vàng và watchdog tự upload đè lên tài khoản.

## 3. Kỹ Thuật Cứu Avatar Từ Thumbnail Lưới Video (Grid Avatar Salvage)
Khi file video gốc trên đĩa đã bị xóa đè, thumbnail bài đăng trên ảnh screenshot Profile là nguồn tư liệu sống duy nhất còn lại để nhận diện nhân vật chính:
1. **Trích xuất đa phương án (Candidate Extraction):**
   - Crop các thumbnail rõ mặt ở hàng 2 và hàng 3 (ảnh selfie cận cảnh đeo kính, ảnh chống cằm áo navy, ảnh áo jersey #4).
   - Upscale 512x512 bằng `Image.Resampling.LANCZOS` và cân chỉnh tâm khuôn mặt.
2. **Khung nhìn tròn thực tế (Circular Masking):**
   - Vẽ mask tròn TikTok mô phỏng avatar thật để operator đánh giá trực quan tỷ lệ khuôn mặt và khoảng thở (headroom).
3. **Bảng đối chiếu 4 panel kèm Vision API Verification:**
   - Panel 1: Avatar lỗi hiện tại (chữ "hôi").
   - Panel 2: Option 1 đề xuất (Selfie cận cảnh sáng rõ).
   - Panel 3: Option 2 (Chống cằm áo thể thao).
   - Panel 4: Option 3 (Áo jersey đỏ hai bím tóc).
   - Soi mắt qua Vision API kiểm tra không bị lẹm viền, không đen màn hình trước khi gửi qua `MEDIA:`.

## 4. Quy Trình Khôi Phục Kênh & Ngăn Chặn Đăng Lệch Ngách (Channel Reversion Protocol)
Khi Operator hỏi *"Lấy lại kênh cũ đăng đc k"*:
1. **Đánh giá thuật toán:**
   - Hoàn toàn khả thi và BẮT BUỘC nên làm: Kênh đã có nền tảng 5 clip thu hút đúng tệp người xem Gen Z/agency (765 view). 3 clip giao thông view chạm đáy (48 view) chứng minh việc lệch ngách bị thuật toán bóp reach.
2. **Hai nhánh xử lý nguồn:**
   - **Nhánh A (Operator cung cấp channel/link):** Dùng `swap_single_folder_pipeline.py` tải trọn bộ 45 clip mới về folder, render và gán lại cho nick.
   - **Nhánh B (Không nhớ tên kênh cũ):** Bốc kênh Creator nữ Gen Z / Daily vlog cùng vibe từ kho 12 Niche Hot. Dọn sạch 43 clip giao thông còn tồn trong folder render, nạp bộ video mới vào.
3. **Cập nhật bộ đếm & Avatar:**
   - Đồng bộ avatar mới vào cả kho gốc và kho render, cập nhật `avatar_replace_queue` về `PENDING`.
   - Cập nhật `Video Đã Đăng = 8` (hoặc số lượng thực tế) trong `Tik<N>.xlsx` để runner không đăng trùng và không đăng lại clip giao thông cũ.
4. **Xử lý các clip đã lỡ đăng lệch ngách:**
   - Chuyển các clip giao thông sang chế độ "Chỉ mình tôi" (Private) để làm sạch lưới Profile, tuyệt đối không dùng raw ADB xoá mù gây rủi ro thao tác.
