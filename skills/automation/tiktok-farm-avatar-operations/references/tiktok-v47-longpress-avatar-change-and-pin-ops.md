# TikTok UI v47+ Long-Press Avatar Change & Pin Top Videos Playbook

## 1. Bối cảnh & Vấn đề (Context & Failure Mode)
Trên các phiên bản TikTok mới (v47.0.3+ trên Android Farm):
- Giao diện Profile thường **KHÔNG hiển thị nút "Sửa hồ sơ" (Edit profile)** mà chỉ hiển thị "Thêm tiểu sử" và các tab Video.
- Nếu bấm nhanh (tap) vào avatar (`com.ss.android.ugc.trill:id/bnr` tại toạ độ ~`800, 350`), TikTok sẽ mở popup **"Tạo một Nhật ký" (Story creator)** thay vì mở menu đổi ảnh.
- Nếu cố gắng tìm nút "Sửa hồ sơ" trong menu 3 gạch hoặc mở setting, quy trình sẽ bị kẹt hoặc mất nhiều bước không cần thiết.

---

## 2. Quy trình đổi Avatar trực tiếp qua Long-Press (Đã kiểm chứng 100%)

### Bước 1: Long-Press vào Avatar
Thực hiện giữ lâu (long press ~1.000ms) vào tâm avatar trên Profile:
```python
# Tọa độ avatar máy 1080x1920: (800, 350)
pin_top_videos.execute_adb_cmd(serial, ["shell", "input", "swipe", "800", "350", "800", "350", "1000"])
```
*Kết quả:* Xuất hiện bottom sheet menu chứa:
- `com.ss.android.ugc.trill:id/dwc`: **"Thay đổi ảnh"** (tại toạ độ ~`540, 1248`).
- `com.ss.android.ugc.trill:id/wb5`: **"Chia sẻ hồ sơ"**.

### Bước 2: Chọn ảnh từ Thư viện
1. Tap vào "Thay đổi ảnh" tại `(540, 1248)`:
   ```python
   pin_top_videos.execute_adb_cmd(serial, ["shell", "input", "tap", "540", "1248"])
   ```
2. Gallery mở ra, tap chọn ảnh đầu tiên (ảnh vừa được push vào thiết bị và quét MediaScanner):
   ```python
   pin_top_videos.execute_adb_cmd(serial, ["shell", "input", "tap", "135", "355"])
   ```
3. Bấm nút **"Tiếp (1)"** (`com.ss.android.ugc.trill:id/y4k` / `q2l` tại `924, 1842`):
   ```python
   pin_top_videos.execute_adb_cmd(serial, ["shell", "input", "tap", "924", "1842"])
   ```

### Bước 3: Lưu Avatar và Bỏ tick Đăng Story
Màn hình cắt ảnh ("Cắt") xuất hiện:
1. **BẮT BUỘC bỏ chọn "Đăng ảnh này lên Nhật ký"**:
   - Element: `com.ss.android.ugc.trill:id/sre` ("Đăng ảnh này lên Nhật ký").
   - Toạ độ checkbox: `(100, 1590)`.
   ```python
   pin_top_videos.execute_adb_cmd(serial, ["shell", "input", "tap", "100", "1590"])
   ```
2. Bấm nút **"Lưu"** (`com.ss.android.ugc.trill:id/tv_confirm` tại `792, 1794`):
   ```python
   pin_top_videos.execute_adb_cmd(serial, ["shell", "input", "tap", "792", "1794"])
   ```
3. Sau khi lưu, TikTok sẽ hiện popup mời chia sẻ ảnh hồ sơ mới. Bấm **Back (Keyevent 4)** để đóng popup:
   ```python
   pin_top_videos.execute_adb_cmd(serial, ["shell", "input", "keyevent", "4"])
   ```
4. Avatar mới đã được cập nhật thành công trực tiếp trên profile.

---

## 3. Quy tắc Pin Top Video (Ghim video nhiều view)

### Cơ chế dồn chỗ (Push Mechanic)
- Khi ghim 1 video, video đó sẽ được đưa vào vị trí **Ghim số 1 (trên cùng bên trái)** và đẩy các video đã ghim trước đó sang phải.
- Nếu muốn video Top 1 (nhiều view nhất, ví dụ 31.3K) nằm ở vị trí số 1 (bên trái), thì thứ tự ghim nên là:
  - Ghim video Top 3 trước (ví dụ 1.4K).
  - Ghim video Top 2 tiếp theo (ví dụ 2.3K).
  - Ghim video Top 1 cuối cùng (31.3K) -> Video 31.3K sẽ chiếm slot số 1 bên trái.

### Thao tác Ghim video:
1. Cuộn đến video cần ghim trên Profile và tap vào video tile.
2. Tại màn hình xem video, tap nút **Share** (`find_share_button` hoặc fallback `(999, 1556)`).
3. Đọc action sheet: tìm item có text/content_desc chứa `"ghim"` hoặc `"pin"`.
4. Tap nút Ghim -> Bấm Back (`keyevent 4`) quay lại Profile.

---

## 4. Chuẩn Headroom cho Avatar Crop (Tránh cắt cụt trán/đỉnh đầu)
- Circular Avatar của TikTok lấy vòng tròn nội tiếp hình vuông $512 \times 512$ ($R = 256$, tâm $256, 256$).
- Khi crop khuôn mặt từ video gốc:
  - Phải chừa khoảng đệm đỉnh đầu (Headroom) ít nhất $20\% - 25\%$ chiều cao khuôn mặt phía trên chân tóc.
  - Tỉ lệ crop chuẩn: `side = int(face_width * 2.3)` đến `2.6`.
  - Tâm crop Y: `center_y = face_y + int(face_height * 0.55)` (để dồn mặt xuống tâm tròn, giữ trọn vòm tóc và cằm bên trong vòng tròn xanh $R=256$).
