# Chống Bịa Đặt Thị Giác Avatar & Quy Trình Trích Xuất Khuôn Mặt Từ Video Gốc (2026-10-13)

## 1. Bối Cảnh Sự Cố & Cạm Bẫy Chết Người (Incident Analysis)
- **Hiện tượng**:
  - Coordinator cần đổi avatar cho kênh TikTok `@hoangthu1804` (Máy 67 - Tik 6 - Folder gốc 467).
  - Coordinator thấy file `D:/video goc/467/avatar.jpg` có sẵn trên đĩa, liền tự động lấy file này vẽ viền tròn xanh làm preview (`tmp_m67_avatar_preview.jpg`) và đính kèm thẻ `MEDIA:` gửi cho User.
  - **Hậu quả nghiêm trọng**: File `avatar.jpg` cũ thực chất là ảnh chụp cận cảnh bề mặt đá granite hồng lốm đốm xám (texture vật liệu/rác crop cũ). Tuy nhiên, Coordinator lại không mở ảnh ra soi mắt mà "tự biên tự diễn" mô tả chi tiết là: *"Nam bạn trẻ tóc đen ngắn, mặc áo khoác màu be/kaki bên ngoài áo thun trắng, biểu cảm mỉm cười thân thiện..."*.
  - User mở ảnh ra thấy một tảng đá màu hồng viền tròn xanh lá cây và chất vấn gay gắt: *"Tại sao tao ép mày soi ảnh trc khi gửi câu tl tao mày vẫn đéo tuân thủ v?"*.
- **Nguyên nhân gốc rễ**:
  1. **Tin tưởng mù quáng file có sẵn**: Giả định sai lầm rằng cứ file có tên `avatar.jpg` trong thư mục gốc là đã chuẩn người thật. Trong thực tế farm, nhiều folder từng bị crop nhầm vải quần jeans, logo, texture nền hoặc ảnh placeholder.
  2. **Bỏ qua Invariant Soi Mắt (`browser_vision`)**: Không gọi tool vision mở ảnh ra xem trước khi gửi tin nhắn, dẫn tới hallucination mô tả sai hoàn toàn sự thật.
  3. **Lỗi nuốt thẻ `MEDIA:` trên Telegram Gateway**: Viết thẻ `MEDIA:<path>` dính liền với đoạn văn bản hoặc trong block markdown khiến parser của Gateway không nhận diện được để upload ảnh, dẫn tới User nhận tin nhắn nhưng không thấy ảnh đính kèm (*"Ảnh đâu mày có gửi đâu"*).

---

## 2. Quy Trình Trích Xuất & Tạo Avatar Chuẩn O(1) Từ Video Gốc

Khi phát hiện `avatar.jpg` cũ không đạt chuẩn hoặc chưa từng được kiểm chứng:

### Bước 1: Trích xuất ứng viên trực tiếp từ file video `.mp4` của kênh
CẤM TUYỆT ĐỐI lấy đại ảnh tĩnh không rõ nguồn gốc. Phải đọc trực tiếp từ các video đã render hoặc video gốc trong $F_{src}$:
```python
import cv2, os

video_path = "D:/video goc/<F_src>/3.mp4"  # Chọn video có mặt nhân vật
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30

cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
candidates = []

# Quét qua các mốc giây trong video (từ giây 3 đến 25)
for sec in range(3, 25):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps))
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, 1.1, 4)
    if len(faces) > 0:
        # Lấy khuôn mặt to nhất (chính diện)
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        fx, fy, fw, fh = faces[0]
        if fw >= 150:  # Đảm bảo khuôn mặt đủ to, rõ nét
            candidates.append((sec, frame, (fx, fy, fw, fh)))
cap.release()
```

### Bước 2: Ghép Mosaic & Soi Mắt Chọn Khung Hình Xuất Sắc Nhất
Ghép 4–6 khung hình ứng viên vào một ảnh mosaic để so sánh biểu cảm (nụ cười, ánh mắt, độ nét):
```python
# Tạo mosaic và dùng browser_vision soi mắt
browser_navigate(url="file:///D:/Taadaa/tmp_cand_mosaic.jpg")
browser_vision(question="Đánh giá biểu cảm khuôn mặt của nhân vật trong các khung hình...")
```

### Bước 3: Crop Vuông $512 \times 512$ Tuân Thủ Invariant Headroom ($cy \approx 0.2 \times H$)
Để khi TikTok cắt tròn không bị cụt đầu hay lẹm cằm:
```python
# Tính toán crop vuông 512x512
crop_size = min(w, 576)
# Đỉnh tóc thường cách đỉnh hộp mặt khoảng 0.45 * fh
# Căn y1 sao cho đỉnh tóc cách mép trên ~30-40px (headroom an toàn)
y1 = max(0, fy - int(fh * 0.45) - 35)
y2 = y1 + crop_size
if y2 > h:
    y2 = h
    y1 = y2 - crop_size

crop_square = frame[y1:y2, 0:crop_size]
crop_512 = cv2.resize(crop_square, (512, 512), interpolation=cv2.INTER_LANCZOS4)

# Tạo ảnh preview viền tròn xanh để kiểm chứng thực tế
mask = np.zeros((512, 512), dtype=np.uint8)
cv2.circle(mask, (256, 256), 256, (255,), -1)
circle_prev = crop_512.copy()
circle_prev[mask == 0] = (circle_prev[mask == 0] * 0.25).astype(np.uint8)
cv2.circle(circle_prev, (256, 256), 256, (0, 255, 0), 2)
cv2.imwrite("D:/Taadaa/avatar_circle_preview.jpg", circle_prev)
```

### Bước 4: Soi Mắt Nghiệm Thu Bắt Buộc Trước Khi Gửi (`browser_vision`)
Trước khi soạn bất kỳ tin nhắn nào cho User:
1. Gọi `browser_navigate("file:///D:/Taadaa/avatar_circle_preview.jpg")`.
2. Gọi `browser_vision("Xác nhận khuôn mặt, tóc, viền tròn...")`.
3. Chỉ khi nhìn thấy tận mắt đúng người thật, đầu không chạm viền tròn xanh thì mới được xác nhận trong báo cáo.

---

## 3. Kỷ Luật Đặt Thẻ `MEDIA:` Tránh Nuốt Ảnh Trên Telegram Gateway
1. **Đứng riêng một dòng độc lập**: Tuyệt đối không để `MEDIA:` trong cùng dòng với text, không nằm sau dấu gạch đầu dòng (`- MEDIA:...`), không nằm trong trích dẫn blockquote (`> MEDIA:...`), không bọc trong backticks.
2. **Định dạng chuẩn xác**:
   ```text
   MEDIA:D:/Taadaa/avatar_circle_preview.jpg
   ```
3. **Cung cấp 2 lựa chọn có đối soát**: Luôn tạo 2 phương án biểu cảm (Phương án 1: Cười mỉm tự nhiên; Phương án 2: Cười tươi rạng rỡ) kèm ảnh preview tròn để User quyết định nhanh chóng.
