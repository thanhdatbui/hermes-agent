# Cứu Hộ Đổi Avatar TikTok v47+ & Chống Khóa Giả Khi Giao Diện Profile Mới (2026-10-15)

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ (Root Cause)

### A. Vấn đề Layout Mới TikTok v47+:
- Trên các phiên bản TikTok v47+, giao diện Profile cá nhân có layout bất đối xứng:
  * Vòng tròn Avatar bị đẩy sang **bên phải** (`bounds: [708,246][1080,636]`).
  * Nút "Sửa hồ sơ" hình chữ nhật to truyền thống ở giữa màn hình **bị ẩn hoàn toàn**.
  * Thay vào đó, ở góc trên bên trái của Profile (`bounds: [24,96][126,204]`, tâm `(75, 150)`) xuất hiện một biểu tượng **cây bút chì nhỏ (Pencil Icon)**.
  * Nếu tap vào Avatar hoặc Note status (`"Bạn có tin vui?"`, `"Tám chuyện nào"`), app sẽ mở popup Story/Status chứ **không mở màn hình Sửa hồ sơ**.

### B. Vấn đề "Báo Xong Ảo" (False Success / Blind Report):
- Runner hoặc subagent thực thi chuỗi lệnh tap không xác thực UI state, bấm nhầm vào popup hoặc thoát về Launcher, sau đó chụp ảnh đen xì (`RGBA (0,0,0,255)`) do màn hình đã tắt (Screen OFF) hoặc app đã thoát.
- Coordinator không kiểm tra ảnh tận mắt hoặc chỉ kiểm tra exit code (`exit 0`), vội vàng báo cáo hoàn thành trong khi thực tế trên thiết bị **avatar vẫn giữ nguyên ảnh cũ**.
- Hậu quả: User bực mình chất vấn gắt gao: *"Là sao mày có đổi ava đâu"*.

---

## 2. Quy Trình Chuẩn Đi Vào "Sửa Hồ Sơ" Trên TikTok v47+ (Bulletproof Navigation)

Khi cần đổi Avatar trên TikTok v47+ mà nút "Sửa hồ sơ" không có ở giữa:

```
[Màn hình Profile]
       │
       ▼ Tap cây bút chì góc trên bên trái: tap(75, 150)
[Màn hình Sửa hồ sơ (Edit Profile)]
       │
       ▼ Tap "Thay đổi ảnh": tap(540, 580)
[Bottom Sheet: Chụp ảnh / Tải ảnh lên / Xem ảnh]
       │
       ▼ Tap "Tải ảnh lên": tap(540, 1637)
[Photo Picker (Gần đây)]
       │
       ▼ Tap tile ảnh đầu tiên: tap(215, 276)
       ▼ Tap "Tiếp": tap(1000, 1850)
[Màn hình Cắt (Crop)]
       │
       ▼ Tap "Lưu": tap(792, 1794) [Bounds: [552,1728][1032,1860]]
       │ (Chờ 5-6s cho upload mạng settle)
[Tự động quay về Sửa hồ sơ]
       │
       ▼ Tap "Quay lại" (84, 78) hoặc keyevent 4
[Quay về Profile]
```

---

## 3. Quy Tắc Bắt Buộc: Xác Thực Đổi Avatar Bằng OpenCV / Vision (Anti-False-Success)

CẤM TUYỆT ĐỐI chỉ dựa vào script exit code 0 để khẳng định đã đổi avatar thành công. BẮT BUỘC thực hiện 2 bước đối soát độc lập:

1. **Kiểm tra Face Detection trên vùng Avatar crop**:
   ```python
   import cv2
   img = cv2.imread(r"D:\Taadaa\tmp\profile_proof.png")
   # Vùng avatar bên phải trên màn hình 1080x1920:
   crop = img[300:636, 708:1080]
   cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
   faces = cascade.detectMultiScale(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 1.1, 4)
   # Nếu ảnh mới là chân dung người thì faces phải > 0
   assert len(faces) >= 1, "Avatar chưa đổi sang ảnh người (không tìm thấy mặt)!"
   ```

2. **Soi Mắt Trực Tiếp Qua Browser Vision**:
   - Mở ảnh `profile_proof.png` qua `browser_navigate` và gọi `browser_vision`.
   - BẮT BUỘC xác nhận tận mắt:
     * Màn hình sáng, đúng profile nickname & username.
     * Vòng tròn avatar hiển thị đúng nhân vật mới (không còn ảnh cũ).
     * Chỉ khi tận mắt thấy avatar mới mới được phép trả lời User và đính kèm thẻ `MEDIA:<path>`.
