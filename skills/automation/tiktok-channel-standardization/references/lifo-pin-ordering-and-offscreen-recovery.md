# TikTok LIFO Pin Ordering & Off-Screen Recovery Protocol

## 1. Cơ Chế Ghim Bài LIFO Của TikTok & Giới Hạn Slot
- **Trần ghim cứng:** TikTok chỉ cho phép tối đa 3 bài ghim trên mỗi trang cá nhân. Nếu tài khoản đã có 3 bài ghim, hành động PIN bài thứ 4 sẽ bị hệ thống từ chối hoặc báo lỗi `PIN_BUTTON_NOT_FOUND` / giới hạn bài ghim.
- **Quy luật thứ tự LIFO (Last In First Out):**
  - Video được bấm PIN sau cùng sẽ luôn nhảy vào **Ô số 1 (Góc trên cùng bên trái, `center_x < 360`)**.
  - Các video đã ghim trước đó sẽ bị đẩy dịch sang phải (Ô số 2: `center_x ~ 540`, Ô số 3: `center_x > 720`).
  - Do đó, để đạt thứ tự hoàn hảo: **Top 1 View (Ô 1) ➔ Top 2 View (Ô 2) ➔ Top 3 View (Ô 3)**, video có view cao nhất bắt buộc phải là video được bấm PIN sau cùng!

## 2. Bẫy Unpin Làm Trôi Video Top Cũ Khỏi Màn Hình (Off-Screen Drift Trap)
- **Hiện tượng:**
  - Giả sử kênh có 3 video ghim: 25.8K (Ô 1), 4.988 (Ô 2), 5.604 (Ô 3), và phát hiện video 12.5K ở hàng dưới chưa được ghim.
  - Khi thực hiện tráo bài ghim:
    1. Hạ ghim 4.988, ghim 12.5K ➔ 12.5K nhảy vào Ô 1 (do ghim sau cùng), đẩy 25.8K sang Ô 2.
    2. Để đưa 25.8K về lại Ô 1, tiến hành UNPIN 25.8K để repin lại.
    3. **Nguy cơ chí mạng:** Video 25.8K là video cũ đã đăng từ lâu. Khi bị UNPIN, nó lập tức quay về vị trí dòng thời gian thực tế bên dưới (ngoài phạm vi hiển thị ban đầu của viewport - off-screen).
    4. Runner chỉ dump UI XML của màn hình hiện tại ➔ không thấy video 25.8K đâu (`cand is None`).
    5. Logic fallback của runner tự động bốc video có view cao nhất trong số các video còn lại trên viewport (chính là video 4.988 vừa bị hạ ghim!) và PIN lại ➔ gây sai lệch kết quả nghiêm trọng!

## 3. Quy Trình 3 Bước Chuẩn Hoá Bài Ghim Hoàn Hảo (Zero-Drift Pipeline)
1. **Bước 1 — Giải Phóng Slot Bằng Video View Thấp Nhất:**
   - Soi danh sách 3 bài ghim hiện hữu, tìm video có `views` thấp nhất.
   - Gọi `_apply_tile_action(serial, cx, cy, "UNPIN")` để hạ ghim video đó.
   - Dump UI XML đối soát xác nhận số bài ghim đã giảm từ 3 xuống 2.

2. **Bước 2 — Cuộn Trang Định Vị & Ghim Video Top View:**
   - Nếu video Top View cần ghim nằm ở nếp gấp dưới (off-screen):
     - Thực hiện vuốt cuộn màn hình: `swipe 540 1600 540 1000 300`.
     - Dump UI XML để lấy tọa độ tâm `(cx, cy)` thực tế của tile video Top View.
     - Gọi `_apply_tile_action(serial, cx, cy, "PIN")`.
   - Vì là video được ghim sau cùng, TikTok sẽ tự động nạp video này vào Ô số 1.

3. **Bước 3 — Pull-to-Refresh & Nghiệm Thu Thị Giác:**
   - Kéo vuốt lên đỉnh trang cá nhân: `swipe 540 500 540 1500 300` (2 lần).
   - Sleep 2-3s để CDN và UI refresh hoàn toàn.
   - Dump UI XML kiểm tra tọa độ và view count của 3 ô đầu:
     - Ô 1 (`center_x < 360`): Video view cao nhất (Top 1).
     - Ô 2 (`360 <= center_x < 720`): Video view nhì (Top 2).
     - Ô 3 (`center_x >= 720`): Video view ba (Top 3).
   - Chụp ảnh screencap màn hình Profile, chạy `run_winrt_ocr.py` lấy fresh receipt và gửi ảnh nghiệm thu `MEDIA:`.
