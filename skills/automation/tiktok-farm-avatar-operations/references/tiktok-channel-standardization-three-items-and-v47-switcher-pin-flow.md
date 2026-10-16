# Quy Trình Chuẩn Hoá 3 Món (Ava - Hashtag - Pin) & Xử Lý Account Switcher / Video Player Mới (2026-10-16)

## 1. Bối Cảnh Nghiệp Vụ "Chuẩn Hoá Kênh"
Khi User gửi ảnh trang cá nhân hoặc lệnh *"Chuẩn hoá kênh này"*, đây là gói quy chuẩn 3 món bắt buộc:
1. **Ghim video (Pin Top):** Quét các video đã đăng trên lưới. Nếu có video $\ge 1.000$ lượt xem chưa ghim $\rightarrow$ Ghim lên đầu trang cá nhân (tối đa 3 video theo quy chuẩn).
2. **Avatar mới:** Trích xuất frame nhân vật mới từ video nguồn của kênh (loại bỏ avatar cũ bị dính phụ đề, logo rác hoặc ảnh lỗi), crop chuẩn $512 \times 512$ (đủ ngũ quan, headroom, viền tròn xanh), upload lên profile và tạo marker `.manual_avatar_locked` tại kho nguồn/render.
3. **Hashtag chuẩn:** Chốt hashtag pool theo đúng niche trong workbook `Tik<N>.xlsx`, tạo marker `.manual_hashtag_locked` để chống cron ghi đè.

---

## 2. Cạm Bẫy Switcher & Điều Hướng Hồ Sơ Tránh Bẫy "Tạo Nhật Ký" (TikTok v47.x)
- **Hiện tượng**:
  - Khi thiết bị đang ở nick khác (ví dụ: `bongbong10045`), trên đỉnh màn hình Hồ sơ thường chèn widget trạng thái *"Bạn có chuyện gì?"* hoặc *"Bạn đang nghĩ gì..."* (`resource-id="com.ss.android.ugc.trill:id/pxu"`).
  - Tapping vào tọa độ giữa đỉnh đầu thường rơi vào widget này hoặc nút `+` trên avatar $\rightarrow$ Mở ra màn hình **Tạo bài đăng Nhật ký (TikTok Story)** hoặc camera thay vì mở Account Switcher.
- **Kỹ thuật mở Account Switcher chuẩn xác**:
  1. **Cuộn nhẹ hồ sơ (Scroll Up / Swipe Up)**:
     - Thực hiện vuốt nhẹ từ dưới lên: `adb shell input swipe 540 1500 540 1000 300`.
     - Thao tác này cuộn phần header cồng kềnh lên, thu gọn thanh header trên cùng lại và làm lộ rõ tiêu đề username dạng dropdown (`resource-id="...:id/pmf"`, bounds `[366,117][720,183]`).
  2. **Tap dropdown username**:
     - Tap vào tâm thanh username thu gọn `(543, 150)` $\rightarrow$ Mở bottom sheet **"Chuyển đổi tài khoản"** (`switcher_dump.xml`).
  3. **Chọn nick mục tiêu**:
     - Định vị bounds của nick trong switcher (ví dụ: `huynhthinh073` tại `[0, 924][1080, 1140]` $\rightarrow$ tap `(540, 1032)`).
     - Đợi 2-3s và tap tab **Hồ sơ** `(970, 1870)` để vào đúng Profile nick mục tiêu.

---

## 3. Quy Trình Ghim Video (Pin Top) Qua Menu 3 Chấm Video Player
- **Hiện tượng**:
  - Trên giao diện TikTok mới, cột nút bên phải của video player không hiển thị nút Chia sẻ (Share / icon mũi tên) đối với video của chính mình, mà thay bằng nút 3 chấm ngang (`...`).
- **Quy trình ghim chuẩn xác**:
  1. Mở video cần ghim từ lưới trang cá nhân: tap vào tâm ô video (ví dụ video 1 tại `(180, 1400)`).
  2. Tại màn hình phát video, tap vào nút **3 chấm (`...`)** ở cột tương tác bên phải tại tọa độ `(1000, 1420)`.
  3. Menu bottom sheet **"Gửi đến"** xuất hiện:
     - Hàng 3 (tác vụ quản lý) hiển thị: *Phân tích, Tải về, Tăng lượt xem, Chiếu, Ghim, Tạo nhóm*.
     - Dùng WinRT OCR hoặc tọa độ chuẩn: Nút **Ghim** nằm tại $X \approx 830$, $Y \approx 1750$ (trong khung $1080 \times 1920$).
  4. Tap vào nút **Ghim** $\rightarrow$ Hệ thống ghim video và trả về thông báo.
  5. Quay lại trang cá nhân kiểm tra: Thumbnail video 1 xuất hiện nhãn đỏ chữ trắng **"Đã ghim"** ở góc trên bên trái.

---

## 4. Quy Trình Thay Avatar & Bỏ Tick Nhật Ký (Uncheck Story Box)
1. **Mở màn hình "Sửa hồ sơ"**:
   - Tap vào nút icon bút sửa hồ sơ bên cạnh Display Name tại tọa độ `(884, 552)`.
2. **Chọn Tải ảnh lên**:
   - Tap dòng text *"Thay đổi ảnh"* tại `(540, 560)`.
   - Bottom sheet hiện 3 tùy chọn: Chụp ảnh, Tải ảnh lên, Xem ảnh.
   - Tap dòng **"Tải ảnh lên"** tại `(540, 1614)`.
3. **Chọn ảnh trong Gallery Picker**:
   - File avatar mới vừa push vào `/sdcard/Pictures/avatar.jpg` và broadcast `MEDIA_SCANNER_SCAN_FILE` sẽ nằm ở ô đầu tiên góc trên bên trái.
   - Tap vào ô ảnh đầu tiên `(180, 350)` $\rightarrow$ Chuyển thành trạng thái tick chọn `(1)`.
   - Tap nút **"Tiếp (1)"** ở góc dưới cùng bên phải tại `(900, 1830)`.
4. **Màn hình Cắt ảnh (Crop Screen) — INVARIANT BỎ TICK NHẬT KÝ**:
   - Kiểm tra tùy chọn: *"Đăng ảnh này lên Nhật ký"*.
   - **BẮT BUỘC ĐỂ TRỐNG (BỎ TICK)**. Nếu đang có dấu tick chọn, phải tap vào checkbox để bỏ tick trước khi lưu (tránh spam feed story vô nghĩa).
   - Tap nút **"Lưu"** màu đỏ ở góc dưới cùng bên phải tại `(800, 1800)`.
5. **Nghiệm thu**:
   - Bấm Back về trang cá nhân.
   - Soi mắt qua `ag_cli.py ask` và `browser_vision` xác nhận avatar mới hiển thị sắc nét, không bị dính phụ đề cũ, trước khi xuất thẻ `MEDIA:`.
