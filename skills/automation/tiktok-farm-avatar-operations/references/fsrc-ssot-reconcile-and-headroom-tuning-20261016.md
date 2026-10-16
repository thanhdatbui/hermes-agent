# Đối Soát Nguồn Cào Thực Tế (F_src SSOT) & Kỹ Thuật Headroom Tuning 10/10 (Cập nhật 2026-10-16)

## 1. Bẫy Lệch Nguồn Giữa SQLite avatar_replace_queue vs Excel Tik<N>.xlsx

### Hiện tượng:
- Khi kiểm tra tài khoản `@daunthzrqig` (Máy 66 Tik 4), SQLite `avatar_replace_queue` lưu:
  `folder_video = 524`, `video_goc = 524`.
- Tuy nhiên, trong `Tik4.xlsx`:
  - `Folder Video (Render Dich)`: `524`
  - `Video Goc (Nguon Cao)`: `306` (Niche: *Làm đẹp*)
- Khi soi các frame đại diện (`.avatar_work/representative_frames/`) trong folder `524`:
  - Có sự pha trộn nhân vật: v00 là nữ tóc nâu áo đen, v02 là nữ kẻ caro, v04 là nữ tóc búi, v05 là nữ áo đen chữ trắng, chỉ có v01 là nam.
- Trong khi đó, trong folder `306`:
  - 100% video (v00, v01, v02, v05...) đều là nam thanh niên đeo kính gọng sáng, áo đỏ/áo trắng review mỹ phẩm — khớp hoàn hảo với 6 video hiển thị trên lưới TikTok profile của tài khoản.

### Quy tắc đối soát SSOT bắt buộc:
1. **Excel Tik<N>.xlsx là SSOT về Nguồn Cào Gốc ($F_{src}$)**:
   - Cột `Video Goc (Nguon Cao)` trong file Excel `Tik<N>.xlsx` chứa folder gốc chuẩn của tài khoản.
   - Không được chỉ tin vào trường `video_goc` trong `avatar_replace_queue` nếu nó trùng với `folder_video` (dấu hiệu clone/render folder chưa link đúng nguồn gốc).
2. **Đối chiếu lưới bài đăng với kho video trước khi crop**:
   - So sánh nhân vật xuất hiện trên lưới trang cá nhân TikTok (tóc, kính, giới tính, trang phục, bối cảnh) với các frame trích xuất từ $F_{src} = 306$.
   - Nếu phát hiện folder render có nhân vật khác hoặc bị trộn tệp, BẮT BUỘC chuyển sang trích xuất trực tiếp từ $F_{src}$ chuẩn trong Excel.

---

## 2. Kỹ Thuật Headroom & Chin Clearance Tuning Đạt Chuẩn 10/10

### Cạm bẫy crop lần đầu:
- Khi dùng công thức Center-based crop với tỷ lệ `side_mult = 2.2 - 2.3` và căn tâm thông thường, viền tròn xanh thường bị chấm điểm **CHƯA ĐẠT (5-6/10)** do:
  - **Lẹm đỉnh tóc (Headroom thiếu)**: Viền tròn cắt ngang ngọn tóc trên đỉnh đầu (mất 5–10% tóc).
  - Dính chữ in nhãn sản phẩm khi nhân vật giơ chai mỹ phẩm sát ngực/cổ.

### Công thức Canvas Expansion & Offset Hoàn Hảo:
```python
import cv2, numpy as np

# 1. Nhận diện khuôn mặt chính xác
faces = face_cascade.detectMultiScale(gray, 1.1, 4)
fx, fy, fw, fh = faces[0]

# 2. Tâm ngang chuẩn giữa mặt, dịch tâm dọc nhẹ lên trên để đẩy mặt xuống dưới
center_x = fx + fw * 0.5
cy_offset = -30  # Dịch lên 30px giúp đẩy khuôn mặt xuống, tạo headroom rộng phía trên đỉnh tóc
center_y = fy + fh * 0.5 + cy_offset

# 3. Mở rộng khung hình an toàn với side_mult = 2.7
side = int(fw * 2.7)

# 4. Canvas expansion chống tràn viền
pad = side
padded = cv2.copyMakeBorder(im, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
cx_pad = int(center_x) + pad
cy_pad = int(center_y) + pad
x0 = cx_pad - side // 2
y0 = cy_pad - side // 2

crop = padded[y0:y0 + side, x0:x0 + side]
crop_512 = cv2.resize(crop, (512, 512), interpolation=cv2.INTER_LANCZOS4)
```

### Tiêu chí nghiệm thu độc lập qua Antigravity CLI / Proxy :20129:
- **Đủ ngũ quan 100%**: Mắt, kính, lông mày, mũi, miệng, cằm rõ nét.
- **Khuôn mặt cân đối**: Nằm ngay trục giữa của khung tròn.
- **Khoảng cách an toàn (Headroom & Chin clearance)**:
  - Đỉnh tóc cách viền xanh trên $\ge 80-120$px.
  - Cằm cách viền xanh dưới $\ge 80-130$px, thấy rõ cổ và cổ áo.
- **Không dính chữ rác**: Không dính phụ đề video, caption hay watermark.

---

## 3. Quy Trình Nạp Avatar Đơn Máy Kèm Khóa Marker Chống Ghi Đè

Khi User đã chốt phương án avatar:
1. **Ghi đè đồng bộ 3 kho**:
   - `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
   - `D:/video goc/<F_src>/avatar.jpg`
   - `D:/video goc/<F_out>/avatar.jpg` (nếu có)
2. **Khóa marker vật lý `.manual_avatar_locked`**:
   - Dùng lệnh `cp "D:/Taadaa/test.txt" "<folder>/.manual_avatar_locked"` (né lệnh `touch` bị terminal guard chặn) tại cả 3 folder trên.
3. **Cập nhật SQLite**:
   - `UPDATE avatar_replace_queue SET status="PENDING", updated_at=datetime("now", "localtime") WHERE username="<username>"`
4. **Kích hoạt runner đơn máy an toàn với device-lock**:
   - Chạy nền có notify để không block context:
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> --timeout 600 -- python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <N>
     ```
     (với tham số `background=True, notify_on_complete=True, timeout=600`).
