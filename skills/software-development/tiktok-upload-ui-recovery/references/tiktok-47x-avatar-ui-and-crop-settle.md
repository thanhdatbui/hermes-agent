# TikTok 47.x Avatar UI Layout, Entry Detection & CDN Settle Invariants

## 1. Hiện tượng & Thay đổi Layout trên TikTok 47.x (Samsung S7 / 1080x1920)

### Cạm bẫy vòng tròn giữa màn hình ("Thêm vào Nhật ký")
- Trên TikTok 47.x, vòng tròn lớn nằm chính giữa màn hình Profile có icon dấu cộng `+` màu xanh ngọc thực chất là **Nút "Thêm vào Nhật ký / Story"**, KHÔNG PHẢI vòng tròn Avatar tài khoản.
- Nếu click vào vòng tròn này, máy sẽ mở màn hình camera/story picker ("Thêm vào Nhật ký") làm state machine kẹt hoặc lầm tưởng là mở ảnh đại diện.
- **Vị trí Avatar thật:** Nằm lệch hẳn sang **góc trên bên phải** (`[800:1040, 350:600]`) ngang hàng với tên tài khoản và username `@handle`.

---

## 2. Đường đi chuẩn xác vào màn hình "Sửa hồ sơ" (Edit Profile)

### Entry Point 1: Icon Bút Chì góc trên bên trái
- Tại màn Profile chính, góc trên bên trái có icon Bút chì:
  - Bounds chuẩn: `[24,96][126,204]` (class `android.widget.ImageView`).
  - Điểm tap: `(75, 150)`.
  - Icon này mở thẳng màn hình **"Sửa hồ sơ"** (`Edit Profile`), bỏ qua mọi nhầm lẫn với Story.
- **Đã tích hợp vào `state_machine.py`:**
  - `_find_profile_edit_button()` ưu tiên gọi `StateMachine._find_new_profile_pencil(xml_text)` với dải bounds tolerance:
    - `0 <= left <= 100`, `60 <= top <= 220`, `60 <= width <= 160`, `60 <= height <= 160`.

### Mở Bottom Sheet Đổi Ảnh
- Trong màn hình "Sửa hồ sơ", tap vào text **"Thay đổi ảnh"**:
  - Bounds: `[396,552][683,609]` (id `com.ss.android.ugc.trill:id/yxg`).
- Bottom Sheet mở lên từ dưới:
  - Chọn **"Tải ảnh lên"** (bounds `[0,1559][1080,1715]`, text/desc `"Tải ảnh lên"`).

---

## 3. Quy trình Chọn ảnh & Cắt (Crop & Save)

1. **Thư viện ảnh (Photo Picker):**
   - Tile ảnh mới nhất (vừa push vào `/sdcard/Pictures/avatar.jpg` và broadcast `MEDIA_SCANNER`):
     - Bounds: `[6,222][269,488]` (id `com.ss.android.ugc.trill:id/owc`).
   - Chọn checkbox hoặc tap trực tiếp tile ảnh -> Bấm nút **"Tiếp"** (`[780,1788][1044,1896]`, id `xyk`).
2. **Màn hình Cắt ảnh (Crop):**
   - Checkbox **"Đăng ảnh này lên Nhật ký"** (`[156,1512][720,1668]`): BẮT BUỘC uncheck nếu đang bật (`checked="true"`).
   - Nút **"Lưu"**: Bounds `[552,1728][1032,1860]` -> Tap tọa độ `(792, 1794)`.

---

## 4. Invariant Đồng bộ CDN & Xung đột Cronjob

### Thời gian chờ CDN Settle
- Sau khi bấm "Lưu", TikTok gửi request HTTP POST lên máy chủ CDN TikTok.
- **BẮT BUỘC:** Chờ ít nhất 8–15 giây cho animation crop đóng và network request hoàn tất 100% trước khi force-stop hoặc thoát về Home.
- Không đọc màn Profile ngay lập tức trong 2-3s đầu vì cache cục bộ chưa render kịp, dễ gây false negative "avatar chưa đổi".

### Tránh xung đột với Cron Clear Cache
- Cronjob dọn dẹp cache `cron_clear_tiktok_cache.py` (chạy qua widget dọn rác màn hình chính) nếu kích hoạt cùng lúc sẽ làm sập/đóng ứng dụng TikTok trong lúc đang tải ảnh.
- **Kỷ luật:** Tạm dừng cron dọn cache khi đang thực thi đợt batch upload avatar cho farm.
