# TikTok Avatar: Quy Trình Nghiệm Thu Chống Ảo Giác Thị Giác & Bẫy Photo Picker Preview (2026-10-13)

**Target:** Taadaa TikTok Farm (Samsung S7, TikTok v47+, Layout C / Biến thể A/B Test)  
**Tác động:** Triệt tiêu hoàn toàn lỗi "báo cáo láo / ảo giác thị giác", bẫy trượt Photo Picker Preview, và crash thiếu RAM (OOM) khi mở Crop Activity.

---

## 1. Phân Tích Cạm Bẫy Chết Người (Incident Analysis)

### 1.1. Ảo Giác Thị Giác Xác Nhận (Confirmation Bias Hallucination)
- **Hiện tượng sự cố**:
  - Coordinator thực hiện đổi avatar cho tài khoản `@cao.m.phng7`.
  - Trong quá trình thao tác, TikTok bị trượt luồng: văng sang webview sự kiện `activity.tiktok.com` (#TikTokAwardsSEA) hoặc văng về launcher/video nền có mảng bokeh mờ.
  - Coordinator chụp ảnh màn hình, crop vùng avatar và đặt câu hỏi mang tính "mớm mồi" (leading question) cho `browser_vision`:
    *Sai:* `"Nhìn vào avatar bên phải: Đã là hình Ông Chú Tâm Lý đeo kính có râu chưa?"*
  - LLM Vision trả lời khẳng định: *"Đúng vậy, avatar đã đổi sang nhân vật hoạt hình Ông Chú Tâm Lý"*.
  - Coordinator lập tức gửi báo cáo DONE kèm ảnh rác/bokeh, khiến User phẫn nộ vì avatar thực tế trên nick **vẫn là người phụ nữ cũ 100%**.
- **Nguyên nhân cốt lõi**:
  1. **Thiếu kiểm chứng định lượng/cấu trúc**: Chỉ dựa vào một câu hỏi vision chủ quan mà không có OCR và thông số kỹ thuật bảo vệ.
  2. **Confirmation Bias**: Khi model nhận câu hỏi giả định sự kiện đã xảy ra, vision rất dễ bị hallucination gán ghép các nét mờ, bóng đổ thành nhân vật mong muốn.

### 1.2. Bẫy Photo Picker: Chế Độ Preview vs Checkbox Tick
- **Cạm bẫy**:
  - Trên TikTok v47+, khi mở `ProfileAvatarChoosePhotoActivity`, nếu tap trúng tâm ô ảnh `(135, 350)` thay vì mép checkbox, TikTok sẽ mở giao diện **Xem trước (Preview) toàn màn hình**.
  - Trong màn hình Preview:
    - Nút "Tiếp" ở góc dưới phải `(923, 1841)` hiển thị màu xám mờ hoặc không kích hoạt.
    - Phải tap trúng **vòng tròn checkbox** ở góc dưới bên trái tại `(84, 1839)` (cạnh chữ *Chọn*) thì nút "Tiếp" mới chuyển sang màu đỏ và kích hoạt luồng chuyển tiếp.
  - Trong màn hình Grid:
    - Vòng tròn checkbox nằm ở góc trên bên phải của tile (ví dụ tile 1 tại `(220, 272)`). Phải tap trúng tọa độ này để chọn trực tiếp mà không bị vào Preview trap.

### 1.3. OOM / Process Eviction Khi Chuyển Từ Picker Sang Crop
- **Cạm bẫy**:
  - TikTok trên máy Samsung S7 (Android 8) chiếm PSS bộ nhớ rất lớn (>600MB).
  - Khi mở đồng thời Picker ➔ Crop Activity, kết hợp với các dịch vụ nền của Samsung/Google (`com.google.android.gm`, `com.android.vending`, `com.sec.android.app.sbrowser`), hệ thống bị cạn RAM tự kill process `com.ss.android.ugc.trill`, khiến máy văng thẳng về Launcher.

---

## 2. Giao Thức Nghiệm Thu Chống Ảo Giác Bắt Buộc (4 Tầng Kiểm Chứng)

CẤM TUYỆT ĐỐI gửi ảnh hoặc báo cáo hoàn tất nếu chưa vượt qua đủ 4 tầng kiểm chứng độc lập:

### Tầng 1: Kiểm Tra Package & Activity Focus
Chạy lệnh O(1) kiểm tra cửa sổ đang hiển thị:
```bash
adb shell dumpsys window windows | grep mCurrentFocus
```
- **Hợp lệ**: `com.ss.android.ugc.trill/...aweme.splash.SplashActivity` (trang Profile) hoặc `ProfileEditActivity`.
- **CỜ ĐỎ - DỪNG NGAY**: Nếu `mCurrentFocus` chứa `LauncherActivity`, `LivePlayActivity`, `SBrowserMainActivity`, hoặc bất kỳ webview nào.

### Tầng 2: Đối Soát Bằng WinRT OCR (OCR-First Grounding)
Chạy script `ocr_boxes.ps1` trên ảnh chụp màn hình Profile:
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:/Taadaa/tools/ocr_boxes.ps1 <duong_dan_anh>
```
BẮT BUỘC tìm thấy các token định danh:
- `@<username>` chính xác của tài khoản mục tiêu.
- `"Đã follow"` / `"Follower"` / `"Thích"`.
- `"Hồ sơ"`.
Nếu OCR phát hiện các từ khóa lạ (`"activity.tiktok.com"`, `"Check in"`, `"Gmail"`, `"Cài đặt"`), chứng tỏ màn hình đã bị drift hoặc bị che popup ➔ CẤM BÁO CÁO!

### Tầng 3: Kiểm Chứng Toán Học Phân Bố Màu (Numeric Pixel Distance)
So sánh giá trị trung bình màu BGR giữa file ảnh gốc cần up (`avatar.jpg`) và ảnh crop vòng tròn avatar thực tế trên trang Profile:
```python
import cv2, numpy as np

img_target = cv2.imread(r"D:/TIKTOK-videonuoinick/<folder>/avatar.jpg")
img_crop = cv2.imread(r"D:/Taadaa/tmp/current_profile_avatar_crop.png")

mean_target = np.mean(img_target, axis=(0, 1))  # [B, G, R]
mean_crop = np.mean(img_crop, axis=(0, 1))

# Tính khoảng cách Euclidean màu sắc
color_dist = np.linalg.norm(mean_target - mean_crop)
# Nếu ảnh mục tiêu tông sẫm/nâu nhưng ảnh crop lại ra màu trắng bạc hoặc xanh lá (lệch > 60 đơn vị):
if color_dist > 60.0:
    raise ValueError(f"Màu sắc avatar trên profile lệch quá lớn ({color_dist:.1f}) so với ảnh gốc! Avatar chưa được cập nhật!")
```

### Tầng 4: Lời Gọi Vision Trung Lập Tuyệt Đối (Zero Leading Prompt)
Khi gọi `browser_vision`, TUYỆT ĐỐI KHÔNG hỏi dạng "Có phải nhân vật X không?".
Bắt buộc dùng prompt trung lập:
```text
"Mô tả chi tiết những gì xuất hiện bên trong vòng tròn avatar này:
- Màu sắc chủ đạo là gì?
- Đối tượng bên trong là người thật, nhân vật hoạt hình, đồ vật, hay mảng màu mờ?
- Khuôn mặt có đặc điểm gì (tóc dài/ngắn, nam/nữ, kính, râu)?
Mô tả khách quan, không suy đoán."
```
Đối chiếu câu trả lời với đặc điểm nhận diện của file avatar gốc.

---

## 3. Quy Trình Khắc Phục Bẫy Picker & Thiếu RAM

1. **Dọn dẹp RAM trước khi thao tác**:
   ```python
   for pkg in ["com.google.android.gm", "com.android.vending", "com.sec.android.app.sbrowser", "com.google.android.apps.photos"]:
       adb.shell(f"am force-stop {pkg}")
   ```
2. **Vào Sửa hồ sơ trên Layout không có nút lớn**:
   - Nếu góc trái trên là icon Add-Friend (`zz5`), tap trực tiếp vào text Bio / Tiểu sử tại `(227, 666)`.
3. **Thao tác Photo Picker chuẩn xác**:
   - Tap "Thay đổi ảnh" `(538, 580)` ➔ Tap "Tải ảnh lên" `(217, 1637)`.
   - **Cách 1 (Grid tick)**: Tap chính xác góc trên phải tile 1 tại `(220, 272)`. Nút Tiếp tại `(910, 1844)` chuyển sang màu đỏ ➔ Tap Tiếp.
   - **Cách 2 (Nếu vào Preview)**: Tap vòng tròn checkbox góc dưới trái tại `(84, 1839)` (cạnh chữ Chọn) ➔ Nút Tiếp góc dưới phải tại `(923, 1841)` chuyển sang đỏ ➔ Tap Tiếp.
4. **Màn hình Crop & Đồng bộ**:
   - Bấm "Lưu" tại `(792, 1794)`.
   - Chờ tối thiểu 8–10 giây cho network request đẩy lên CDN hoàn tất trước khi back về Profile.
