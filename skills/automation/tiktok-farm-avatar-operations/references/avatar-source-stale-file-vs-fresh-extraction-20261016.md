# Cạm bẫy Avatar Cũ Trên Đĩa vs. Trích Xuất Frame Mới Từ Video (2026-10-16)

## Root Cause Được Phát Hiện

### Lỗi Ngộ Nhận "Avatar Cũ = Avatar Tốt"
- **Hiện tượng:** Trong session này, `D:/TIKTOK-videonuoinick/468/avatar.jpg` đã tồn tại từ trước (43KB, chụp ngón tay cầm dây cáp — ảnh công nghệ/vật phẩm, không phải bạn nữ creator). Coordinator đọc file, thấy Haar face detection trả về 1 khuôn mặt, và suýt dùng file cũ này làm avatar mới.
- **Điểm kiểm tra sai:** Face detection `haarcascade_frontalface_default.xml` bắt nhầm connector/cáp thành "khuôn mặt" (false positive phổ biến với vật kim loại có góc cạnh phản chiếu).
- **Hậu quả tiềm năng:** Nếu không có lỗi tham chiếu ảnh preview (User hỏi "Mày có xem hình trước khi gửi không?"), avatar dây cáp sẽ được upload thay cho ảnh bạn nữ creator.

## Bằng Chứng Phát Hiện Lỗi
User gửi lại ảnh preview với comment: *"Mày có xem hình trước khi gửi tao k đấy"* — tức là ảnh preview gửi đi là ảnh dây cáp (vật phẩm công nghệ), không phải chân dung creator.

## Quy tắc Kiểm Chứng Bắt Buộc (Bổ Sung Vào Flow)

### 1. CẤM Dùng File avatar.jpg Sẵn Có Trên Đĩa Không Qua Soi Mắt
- Trước khi dùng file `avatar.jpg` có sẵn trong kho, **BẮT BUỘC** trích xuất và xem thử ít nhất 2-3 frame từ video nuôi thực tế tại `D:/TIKTOK-videonuoinick/<folder>/`.
- Nếu `avatar.jpg` sẵn có không khớp với chủ thể kênh (nhìn thấy vật phẩm, logo, ảnh phong cảnh, ảnh tĩnh thay vì gương mặt creator), **BẮT BUỘC trích xuất frame mới**.

### 2. Haar Cascade = Không Đủ Để Xác Nhận Chủ Thể
- `haarcascade_frontalface_default.xml` bắt false positive trên dây cáp, bo mạch, đèn LED, vật thể kim loại có góc cạnh.
- Tiêu chuẩn kiểm chứng hợp lệ: **Phải gửi ảnh preview (MEDIA: hoặc browser_vision) cho User xác nhận** trước khi đồng bộ và nạp lên máy.

### 3. Quy Trình Chuẩn Trích Xuất Frame Khi avatar.jpg Đã Tồn Tại
```python
import cv2, os

# 1. Load avatar.jpg hiện tại
ava = cv2.imread(f'D:/TIKTOK-videonuoinick/{folder}/avatar.jpg')

# 2. Xem thumbnail
preview_src = os.path.join('D:/Taadaa/tmp', f'prev_{folder}_existing.jpg')
cv2.imwrite(preview_src, ava)

# 3. BẮT BUỘC trích xuất thêm frame từ video 7.mp4, 6.mp4 để đối chiếu
for vid in ['7.mp4', '6.mp4']:
    cap = cv2.VideoCapture(f'D:/TIKTOK-videonuoinick/{folder}/{vid}')
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    for sec in [1.0, 2.0, 3.0]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * sec))
        ret, frame = cap.read()
        if not ret: continue
        cv2.imwrite(f'D:/Taadaa/tmp/cand_{folder}_{vid}_{sec}s.jpg', frame)
    cap.release()
# 4. Gửi preview qua browser_vision so sánh và CHỈNH xem đúng chủ thể chưa
```

### 4. Grid Frame Extraction → Mosaic Preview → browser_vision → Gửi MEDIA Cho User
- Chuẩn quy trình: Trích frame → tạo mosaic preview → browser_vision soi mắt kiểm tra → gửi `MEDIA:<path>` + mô tả bằng chứng thị giác.
- **CẤM gửi `MEDIA:` ảnh preview mà không có xác nhận vision trước**.

## Công Thức Trích Frame Đúng (1080x1920 video dọc, face ở 15-25% từ trên)
```python
# Tìm face đúng phần trên (không phải giữa hay dưới ảnh)
for (x, y, w, h) in faces:
    if w > 80 AND y < frame.shape[0] * 0.5:  # chỉ lấy face phần trên
        cx, cy = x + w // 2, y + h // 2
        size = int(max(w, h) * 1.8)
        x1 = max(0, cx - size // 2)
        y1 = max(0, cy - int(size * 0.45))  # headroom chuẩn 45%
        x2 = min(frame.shape[1], x1 + size)
        y2 = min(frame.shape[0], y1 + size)
        crop = frame[y1:y2, x1:x2]
        crop_512 = cv2.resize(crop, (512, 512))
```
