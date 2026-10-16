# Bẫy Dương Tính Giả Haar Cascade Khi Trích Xuất Avatar & Kỷ Luật Soi Mắt Pre-Send Candidate (2026-10-17)

## Bối cảnh & Hiện tượng (Incident)
Khi thực hiện chuẩn hoá avatar cho tài khoản TikTok `@inhkhoa0211` (Máy 77, Tik 6, F_out=614, F_src=477):
- Avatar hiện tại trên profile là ảnh một cô gái trẻ, trong khi toàn bộ video trên kênh là của một chú trung niên mặc áo cổ tàu đen/be chia sẻ đạo lý, thói quen sống.
- Subagent worker được giao trích xuất khuôn mặt từ video `614/1.mp4` và `614/4.mp4` bằng `haarcascade_frontalface_default.xml` ở mốc thời gian cố định (5s và 6s).
- Subagent báo cáo hoàn thành (exit 0) và sinh ra 2 file candidate.
- **Thực tế khi Coordinator soi mắt bằng vision trước khi gửi:**
  - **Option 1:** Hoàn toàn không có mặt người! Ảnh bị nhòe và phóng to vào một góc kệ gỗ/nội thất (Haar cascade bắt nhầm vân gỗ thành khuôn mặt).
  - **Option 2:** Khung hình zoom sát vào vành tai và thái dương, trán và cằm bị viền tròn cắt lẹm 100%.
- Nếu không có **Invariant LLM Soi Mắt Đọc Ảnh Trước Khi Gửi**, Coordinator sẽ gửi 2 ảnh rác này lên Telegram cho User, gây thất bại nghiêm trọng về chất lượng vận hành.

---

## Nguyên nhân gốc rễ (Root Cause)
1. **Bẫy Haar Cascade trên video chuyển động:**
   - Bộ lọc Haar cascade cổ điển rất nhạy cảm với các đường vân tương phản ánh sáng (vân gỗ, họa tiết trang trí, nếp gấp rèm/áo, vành tai), dễ sinh False Positive nếu tham số `scaleFactor` và `minNeighbors` để quá lỏng (`scaleFactor=1.1, minNeighbors=3`).
   - Mốc thời gian cố định (ví dụ đúng giây thứ 5) có thể rơi vào lúc nhân vật đang cúi đầu, chớp mắt, quay lưng, hoặc khung hình bị chuyển cảnh (transition).
2. **Ảo giác hoàn thành của Worker (Exit Code 0 Illusion):**
   - Script chạy trích xuất và crop ảnh thành công về mặt I/O (file tồn tại, đúng kích thước 512x512) nên worker tự tin báo cáo thành công mà không hề biết nội dung ảnh là rác.

---

## Giải pháp & Quy chuẩn bắt buộc (Actionable Pattern)

### 1. Quét đa mốc thời gian & Lọc kích thước khuôn mặt (Multi-timestamp Face Probe)
Không trích xuất tại 1 timestamp duy nhất. Bắt buộc quét lướt qua tối thiểu 4–5 mốc thời gian trong video (`sec in [3, 5, 8, 10, 12]`):
```python
cas = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
# minNeighbors >= 5 để triệt tiêu false positive vân gỗ/đồ vật
faces = cas.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5)
# Bắt buộc lọc diện tích khuôn mặt trong video 1080x1920:
# Mặt người dẫn chuyện tối thiểu fw >= 200, fh >= 200
valid_faces = [f for f in faces if f[2] >= 200 and f[3] >= 200 and 0.8 <= f[2]/f[3] <= 1.25]
```

### 2. Quy chuẩn Center Crop theo tỷ lệ vàng (Section 13)
- Tâm crop: `cx = fx + fw // 2`, `cy = fy + int(fh * 0.55)` (hơi hạ thấp tâm xuống vùng sống mũi/nhân trung để lấy đủ cằm).
- Kích thước hộp vuông: `side = int(fw * 1.5)` (đảm bảo headroom $\ge 30\text{px}$ và chin clearance $\ge 20\text{px}$, không bị viền tròn cắt cằm).
- Clamp an toàn toạ độ: tránh lỗi out-of-bounds tràn mép ảnh video.

### 3. Kỷ luật Pre-Send Candidate Vision Gate
Trước khi đính kèm `MEDIA:<candidate_circle.jpg>` gửi User duyệt:
- BẮT BUỘC gọi `browser_vision` (hoặc model vision qua proxy `:20129`) kiểm tra:
  1. Có đúng khuôn mặt người chính diện không?
  2. Bố cục ngũ quan (mắt, mũi, miệng, cằm) có nằm trọn trong viền tròn xanh không?
  3. Có bị phụ đề / caption to che mặt không?
- Nếu phát hiện nhòe, lệch góc, bắt nhầm tai/đồ vật $\rightarrow$ Tự động reject nội bộ và probe sang video/timestamp khác, TUYỆT ĐỐI KHÔNG gửi ảnh lỗi cho User.

### 4. Quy trình nghiệm thu sau khi nạp trên Farm (Capture-Before-Teardown)
- Khi chạy avatar-only runner (`run_avatar_batch_3accs.py`), kiểm tra artifact tại `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\`:
  - `avatar-save-surface-guard.png`: Màn hình cắt ảnh native của TikTok (xác nhận đúng ảnh mới trong khung cắt).
  - `avatar-uploaded-confirmed.png`: Màn hình Sửa hồ sơ (xác nhận vòng tròn avatar đã cập nhật ảnh mới, đúng tên và username).
- Soi mắt kiểm chứng cả 2 ảnh trước khi gửi báo cáo nghiệm thu hoàn tất cho User.
