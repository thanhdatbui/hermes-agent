# Avatar Candidate Generation & Logo/Emblem Trap Prevention (2026-10-13)

## 1. Căn Nguyên Sự Cố: Bẫy Logo/Huy Hiệu (Logo Trap vs Human Subject)
Trên các kênh TikTok nuôi chuyển giao ngách hoặc kho video cũ:
1. **Lẫn Slide Bài Giảng / Tài Liệu**:
   - Kho video cũ từng chứa các video bài giảng ôn thi THPT, infographic, tài liệu học tập có chèn logo huy hiệu Bộ Giáo Dục Đào Tạo (GDĐT) hoặc biểu trưng trường học ở góc trên bên trái.
   - Các script tự động cắt frame đại diện hoặc thuật toán crop ngẫu nhiên dễ nhận diện nhầm hình tròn/huy hiệu ở góc này thành khuôn mặt, dẫn đến việc cắt ra avatar là logo GDĐT thay vì chân dung nhân vật chính chủ.
2. **Báo Cáo Khống Do Dùng Screenshot Cũ (Stale Screenshot Trap)**:
   - Coordinator hoặc subagent lấy lại file ảnh `avatar_final_result.png` / `avatar_verified_zoom.jpg` từ phiên trước đó để soi vision và kết luận đã đổi thành công, trong khi trên thiết bị thật lệnh đổi avatar chưa từng được thực thi hoặc app đang ở tài khoản khác trong Switcher.
   - Hậu quả: User kiểm tra trên web/app thì avatar trên server TikTok vẫn là logo cũ, gây bức xúc nghiêm trọng.

---

## 2. Quy Trình Trích Xuất Avatar Chân Dung Người Thật Chuẩn O(1)
1. **Lọc Bỏ Slide & Video Rác**:
   - Kiểm tra các video trong kho `D:/video goc/<folder>/` hoặc `D:/TIKTOK-videonuoinick/<folder>/`.
   - Tuyệt đối không trích xuất frame từ video slide tài liệu, bài giảng chữ, mindmap.
   - Chọn video có cảnh quay người thật (selfie, vlog, công sở, sinh hoạt đời sống như `1.mp4`).
2. **Trích Xuất Frame Chất Lượng Cao**:
   - Trích xuất frame ở khoảng giây 2.0 – 4.0 khi nhân vật nhìn thẳng vào ống kính, biểu cảm tự nhiên, ánh sáng rõ nét, không bị nhòe chuyển động.
3. **Bố Cục Cắt Vuông 512x512 Chuẩn Invariant**:
   - Kích thước: `512x512` (chuẩn avatar TikTok).
   - Tọa độ tâm mặt: $cy \approx 0.2 \times H$ (khoảng 15–25% từ trên xuống).
   - Khuôn mặt chiếm 45–55% diện tích hình tròn hiển thị của TikTok.
   - Giữ khoảng trống đỉnh đầu (headroom), cấm cụt đầu hoặc lẹm cằm.

---

## 3. Quy Trình Duyệt Avatar Trước Khi Đổi (User Pre-Approval Invariant)
Khi tài khoản từng bị sai lệch avatar, dính logo rác hoặc User yêu cầu duyệt trước:
1. **Tạo Ảnh So Sánh 2–4 Phương Án (Preview Comparison)**:
   - Ghép 2 hoặc 4 phương án avatar người thật cạnh nhau (ví dụ: góc chính diện áo hồng vs góc năng động áo trắng đeo balo, góc công sở bàn làm việc).
   - Lưu thành file tổng hợp: `D:/Taadaa/tmp/avatar_preview_comparison.jpg` hoặc `real_female_candidates.jpg`.
2. **Soi Mắt Bắt Buộc Qua Vision (Gate 6)**:
   - Dùng `browser_vision` mở ảnh tổng hợp ra kiểm tra tận mắt:
     * Xác nhận 100% không còn dính logo/huy hiệu nào.
     * Xác nhận rõ mặt người, sắc nét, đúng chủ thể kênh.
3. **Trình Báo & Chờ User Duyệt**:
   - Gửi ảnh kèm thẻ `MEDIA:<path>` và mô tả ngắn gọn từng phương án để User lựa chọn.
   - Chỉ khi User chốt phương án cụ thể mới tiến hành nạp ảnh vào kho và đẩy lên thiết bị.

---

## 4. Kiểm Soát Thiết Bị & Tránh Lệch Tài Khoản Trước Khi Đổi
1. **Xác Minh Đúng Nick Đang Mở**:
   - Trên Layout C hoặc bất kỳ layout nào, trước khi bấm "Sửa hồ sơ", BẮT BUỘC kiểm tra text hiển thị `@<username>` trên màn hình Profile.
   - Nếu màn hình đang ở nick khác trong Switcher, phải mở Switcher và chuyển sang đúng nick mục tiêu trước.
2. **Dọn MediaStore Triệt Để**:
   - Xóa toàn bộ rác ảnh screenshot trong MediaStore trước khi push file avatar mới để Photo Picker không chọn nhầm ảnh chụp màn hình.
