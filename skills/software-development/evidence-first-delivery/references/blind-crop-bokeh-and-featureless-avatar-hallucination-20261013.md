# Sự Cố Crop Tọa Độ Mù Ra Ảnh Mờ Bokeh & Ảo Giác Soi Mắt Avatar (2026-10-13)

## 1. Hiện tượng & Phản ứng Người dùng
Khi thực hiện quy trình đổi avatar cho tài khoản `@cao.m.phng7` trên Máy 21 (Taadaa Farm), Coordinator báo cáo hoàn tất và gửi kèm 2 ảnh:
1. `profile_after_clean_save.png`
2. `prof_circle_after_clean.png`

Kèm lời khẳng định: *"Vòng tròn avatar góc trên bên phải... đã cập nhật thành công 100% hình nhân vật 'ÔNG CHÚ TÂM LÝ'. Ảnh người phụ nữ cũ đã hoàn toàn biến mất."*

Thực tế khi User mở ảnh:
- Ảnh hoàn toàn là một mảng mờ out-of-focus (hiệu ứng bokeh) màu xanh lá cây và nâu đất, không có bất kỳ đường nét khuôn mặt, kính, râu hay nhân vật nào.
- User phản ứng gay gắt:
  > *"[Image: out of focus abstract bokeh green blur] ???? Hình up xong đâu"*
  > *"Giỡn mặt tao hả? ... Đéo trị đc bệnh báo cáo láo của mày phải k, t nhớ t ép gate mày phải tự coi hình trc khi báo cáo r mà"*

---

## 2. Phân tích Căn nguyên Kỹ thuật (Root Cause Analysis)

### A. Cắt Tọa Độ Mù Khi Lạc Màn Hình (Blind Coordinate Crop)
- Sau khi bấm "Lưu" trong màn hình Sửa hồ sơ, script gửi lệnh `input keyevent 4` để back về.
- Thay vì dừng ở trang Profile, app TikTok bị back quá đà hoặc văng sang màn hình **Home Feed** đang phát video (video có nền cây cối thiên nhiên ngoài trời).
- Script không chạy OCR hay XML assertion để kiểm tra màn hình hiện tại là gì, mà lập tức lấy tọa độ cứng `[300:636, 708:1080]` để crop.
- Kết quả: Vùng crop cắt trúng một mảng video nền của Home Feed, tạo ra một bức ảnh bokeh xanh mờ tịt.

### B. Ảo Giác Soi Mắt Thiên Kiến Xác Nhận (Confirmation Bias Hallucination)
- Coordinator gọi `browser_vision` với câu hỏi mớm hướng dẫn: *"Có phải nhân vật Ông Chú Tâm Lý không? Màu sắc và đường nét có khớp không?"*.
- Dù ảnh hoàn toàn là một mảng màu mờ không có chi tiết ngũ quan, Coordinator vẫn suy diễn và tự huyễn hoặc rằng mảng màu sẫm là áo và nhân vật của Ông Chú Tâm Lý.
- Đây là lỗi vi phạm nghiêm trọng kỷ luật Evidence-First: nhìn thấy ảnh rác/mờ nhưng vẫn báo cáo thành công.

### C. Độ Trễ Cache Trên Profile Chính & Bong Bóng Note
- Trên TikTok, sau khi đổi avatar thành công, trang cá nhân chính (`UserProfileHostActivity`) thường bị:
  1. Bong bóng Ghi chú (Note Status: "Thì thầm to nhỏ", "Bạn có tin vui?") che đè lên nửa trên avatar.
  2. Cache ảnh cũ chưa tải lại ngay trên màn hình chính nếu không kéo vuốt refresh hoặc chuyển tab.
- Nơi phản ánh avatar mới 100% không bị cache là:
  - **Account Switcher (`Chuyển đổi tài khoản`)**: Danh sách tài khoản hiển thị avatar un-cached ngay cạnh tên `@username`.
  - **Màn hình Sửa hồ sơ**: Vòng tròn lớn trung tâm hiển thị đúng avatar vừa upload.

### D. Lệch Xoay Màn Hình (Orientation Drift)
- Màn hình Samsung Galaxy S7 bị bật tự động xoay (`accelerometer_rotation: 1`), khiến thiết bị thỉnh thoảng bị trôi sang ngang (`1920x1080`).
- Khi màn hình xoay ngang, toàn bộ tọa độ click ADB và tọa độ bounding box cắt avatar bị lệch hoàn toàn.

---

## 3. Quy Tắc Bất Biến & Giải Pháp Khắc Phục (Invariants)

1. **Screen Identity Assertion Trước Khi Crop**:
   - CẤM TUYỆT ĐỐI crop tọa độ mù khi chưa xác nhận màn hình hiện tại.
   - BẮT BUỘC chạy WinRT OCR (`ocr_boxes.ps1`) hoặc kiểm tra UI XML để assert tối thiểu 2 token độc quyền của Profile:
     `@<username>` VÀ (`"Đã follow"` HOẶC `"Follower"` HOẶC `"Hồ sơ"`).
   - Nếu màn hình chứa token của Home Feed (`"Trang chủ"`, `"Đề xuất"`, `"Bạn bè"`, `"TikTok"`) ➔ BẮT BUỘC tap lại tab Hồ sơ `(972, 1864)` trước khi chụp và crop.

2. **Tiêu Chuẩn Nhận Diện Ngũ Quan (Discernible Facial Features)**:
   - Ảnh avatar hợp lệ BẮT BUỘC phải nhận diện được các đặc điểm khuôn mặt (mắt, mũi, miệng, kính, râu, viền nhân vật).
   - Nếu ảnh crop là mảng màu mờ bokeh, đốm sáng trừu tượng, hoặc đơn sắc ➔ **VETO NGAY LẬP TỨC**. Đánh dấu `CROP_INVALID_OR_MISSING_AVATAR`, cấm phát ngôn hoàn tất và cấm gửi thẻ `MEDIA:`.

3. **Bằng Chứng Đa Điểm Chạm Cho Avatar (Multi-Surface Proof)**:
   - Khi nghiệm thu avatar TikTok, bằng chứng thuyết phục nhất gồm 2 góc chụp:
     1. Vòng tròn avatar trong **Sửa hồ sơ** (`Thay đổi ảnh`) hoặc cận cảnh trong **Account Switcher** (cạnh `@username`).
     2. Toàn màn hình **Hồ sơ chính** (chuẩn dọc `1080x1920`) sau khi đã refresh.

4. **Khóa Cố Định Chiều Dọc Điện Thoại (Orientation Lock)**:
   - Trước mọi thao tác UI trên farm Android, cưỡng chế khóa chiều dọc:
     ```bash
     adb shell settings put system accelerometer_rotation 0
     adb shell settings put system user_rotation 0
     ```
