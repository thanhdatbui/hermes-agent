# Avatar Upload: CDN Upload Latency, No Early Back, and Visual Next Fallback (2026-09-03)

Bài học và quy chuẩn xử lý sự cố upload avatar TikTok trên Phone Farm Samsung S7 (repo `D:\Taadaa\Tiktok-video`).

## 1. Nguyên nhân gốc rễ lỗi "Báo hoàn thành nhưng avatar vẫn silhouette / camera icon"

1. **Cắt ngang tiến trình Upload lên CDN (Early Back / Force-Stop):**
   - Sau khi bấm `Lưu` (`bounds=[552,1728][1032,1860]` hoặc `(792, 1794)`), TikTok cần 5–10 giây để nén ảnh và gửi request POST tải ảnh lên server CDN của TikTok.
   - Code cũ gọi ngay `adapter.back()` và `am force-stop com.ss.android.ugc.trill` sau 4 giây. Lệnh Back/Force-stop này lập tức ngắt tiến trình upload ngầm, làm server TikTok không nhận được ảnh và avatar bị giữ nguyên trạng thái cũ.
   - **Quy tắc:** TUYỆT ĐỐI KHÔNG gọi `adapter.back()` sau bước lưu avatar. Phải chờ màn hình Crop tự động đóng và TikTok chuyển về lại màn hình Sửa hồ sơ / Profile (tối thiểu 8–12s) trước khi force-stop về Home.

2. **Kẹt màn hình Chọn ảnh khi UIAutomator dump XML rỗng (Empty XML):**
   - Trên một số máy S7 / Android 7 cũ, `uiautomator dump` trả về file XML 0-byte (hoặc timeout).
   - Khi chọn ảnh đầu tiên, nút `Tiếp (1)` màu đỏ ở góc dưới phải (`bounds=[820,1750][1050,1870]`, tâm `(935, 1810)` / `(924, 1842)`) không thể nhận diện qua XML.
   - Luồng polling cũ trong `_save_avatar_without_story` chỉ chờ XML hoặc `_is_avatar_save_surface_visual` (yêu cầu màu đỏ trải dài cả 2 nửa) nên bị kẹt hết 25s deadline dẫn đến lỗi `AVATAR_CROP_OPEN_FAILED`.
   - **Quy tắc:** Thêm kiểm tra `_is_avatar_next_surface_visual(visual_crop)` trong vòng lặp polling để tự động tap tọa độ `(924, 1842)` / `(935, 1810)` ngay cả khi XML hoàn toàn rỗng.

3. **Xác minh Avatar Live bằng Độ lệch màu RGB (RGB Variance):**
   - Không kết luận upload avatar thành công chỉ dựa trên wrapper exit code 0.
   - Vùng avatar trên Profile (`(440, 230, 640, 430)`):
     - **Chưa có avatar / Lỗi mạng:** Là ảnh silhouette bóng xám thuần túy (`R = G = B ≈ 106.6`, Standard Deviation `std_dev < 20`) hoặc icon camera đỏ nền xám.
     - **Đã up avatar thành công:** Là ảnh thật có màu sắc phong phú, độ lệch chuẩn các kênh RGB `std_dev > 50` và trung bình màu khớp với source `avatar.jpg`.
