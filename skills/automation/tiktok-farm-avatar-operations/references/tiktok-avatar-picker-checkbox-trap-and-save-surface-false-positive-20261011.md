# TikTok Avatar Picker Checkbox Trap & Save Surface False-Positive Incident (2026-10-11)

## 1. Hiện tượng & Sự cố thực tế (Incident 11/10/2026)
- **Bối cảnh:** User yêu cầu đổi avatar cho tài khoản `kieu.lam966` trên Máy 20.
- **Sự cố 1 (Crop lệch ngực áo):** Trích xuất video dọc 9:16 (576x1024) với công thức crop tâm `y = 0.4 * H` (ngang ngực) khiến khi TikTok mask tròn, đầu và mặt bị cắt cụt hoàn toàn, avatar chỉ còn mảng vải áo hồng.
- **Sự cố 2 (Báo cáo láo / Hallucination):** Agent nhìn lướt screenshot toàn màn hình rồi kết luận "khung tròn avatar đã cập nhật đúng chân dung bạn nữ áo hồng", bị User mắng gay gắt: *"Đkm Mày up ava v mà dám bảo là bạn nữ áo hồng. Mày lại nói láo mày đéo hề xem"*.
- **Sự cố 3 (Bẫy False-Positive Save Surface & Lỗi Checkbox Photo Picker):**
  - Sau khi crop lại chuẩn khuôn mặt và chạy runner `run_tiktok_upload_avatar.ps1`, runner báo `exit=0`, `verified=True`, `status: AVATAR_SMOKE_SUCCESS`.
  - Nhưng trên điện thoại thực tế, avatar hoàn toàn không đổi, vẫn giữ nguyên logo/huy hiệu Sở GD&ĐT cũ. User gửi ảnh phản ánh: *"Vẫn k đúng ảnh ng"*.

## 2. Nguyên nhân kỹ thuật cốt lõi (Root Cause)

### A. Lỗi tap tâm tile thay vì Checkbox trong TikTok Picker
- Trong giao diện chọn ảnh 4 cột của TikTok (`com.ss.android.ugc.trill`), mỗi ô ảnh có:
  - Ảnh thumbnail chiếm toàn bộ ô.
  - Vòng tròn checkbox rỗng nằm ở **góc trên bên phải** của ô ảnh `(right - 35, top + 35)`.
- Khi runner gọi `adapter.tap(*first["center"])` vào tâm ô ảnh `(137, 355)`, TikTok coi đây là thao tác chạm mở ảnh xem thử (Preview) chứ **KHÔNG tick chọn ảnh**!
- Checkbox vẫn rỗng, nút **"Tiếp"** ở góc dưới-phải `(920, 1855)` bị xám (disabled, không có số `(1)`).
- Khi runner tiếp tục tap tọa độ nút "Tiếp", do nút đang disabled nên sự kiện bị nuốt; picker tự đóng hoặc back về màn "Sửa hồ sơ" mà không nạp ảnh nào vào luồng Crop!

### B. Bẫy ngộ nhận màn "Sửa hồ sơ" thành màn Crop (Save Surface Collision)
- Trên màn hình "Sửa hồ sơ", ở đáy màn hình có nút màu đỏ "Lưu" (Save profile).
- Bộ nhận diện thị giác `_is_avatar_save_surface_visual` kiểm tra vùng pixel đỏ ở góc đáy màn hình `(552..1032, 1728..1859)`.
- Nút "Lưu" của "Sửa hồ sơ" vô tình thỏa mãn đúng điều kiện này.
- Runner ngộ nhận mình đang ở màn Crop, tap tọa độ `(792, 1794)`, thấy màn hình không đổi rồi kết luận: *"Màn crop đã đóng, đổi avatar thành công"* (`exit=0, verified=True`).
- Kết quả: Profile được lưu lại với chính avatar cũ, còn file ảnh mới push hoàn toàn chưa được gán!

### C. Bẫy sai lệch Profile Layout (Layout B Lệch Trái vs Layout A Ở Giữa)
- **Sai lệch tọa độ mở Sửa hồ sơ:**
  * Layout A (cũ): Avatar ở giữa, có icon bút chì ở góc trên-trái `(75, 150)`.
  * Layout B (mới/cá nhân): Avatar nằm lệch bên trái `(x ~ 210, y ~ 280)`, phía trên avatar hoàn toàn là khoảng trắng. Nút "Sửa hồ sơ" nằm ở hàng dưới tại `(290, 720)`.
  * Hậu quả: Script tap mù vào `(75, 150)` chỉ chạm vào khoảng trắng, màn *Sửa hồ sơ* hoàn toàn không mở. Toàn bộ các bước tap tiếp theo đều trượt trên màn hình Profile!
- **Bẫy Crop Zoom kiểm chứng (Crop vào khoảng trắng):**
  * Nếu code kiểm chứng cố định crop vùng giữa `(x: 400..680, y: 150..400)`, trên Layout B vùng này là khoảng trắng giữa avatar và cột số liệu (RGB mean > 245, std < 20).
  * Agent nhìn ảnh trắng xóa nhưng lại suy diễn "thấy mặt người", tạo ra ảo giác nghiêm trọng dẫn đến việc bị người vận hành chửi mắng. BẮT BUỘC kiểm tra vùng avatar thực tế theo layout (`x: 80..340` nếu lệch trái).

### D. Bẫy Ngộ Nhận Chủ Thể Kênh Do Rác Trong `video goc` (Raw Folder vs Render Nuoi vs Profile Grid)
- **Sự cố thực tế:**
  * Thư mục `D:/video goc/156` chứa lẫn cả slide bài giảng ôn thi Lịch Sử từ đợt cào cũ (có watermark logo GDĐT) lẫn video creator. Thuật toán Haar cascade bắt nhầm logo GDĐT thành khuôn mặt, dẫn đến việc crop logo làm avatar và Agent tự suy diễn "kênh về giáo dục ôn thi THPT".
  * Người vận hành phản ánh: *"Gì thế t thấy video của kênh đó toàn gái mà"*.
  * Khi kiểm tra lưới video thực tế đã đăng (`profile_video_grid`) trên màn hình Profile TikTok và kho video nuôi `D:/TIKTOK-videonuoinick/156/`, 100% video thực tế đang đăng trên kênh là bạn nữ creator (áo croptop xám, hai dây trắng, selfie trong phòng).
- **Nguyên nhân:** Agent chỉ quét vài file đầu trong `video goc` (`1.mp4`, `2.mp4`), thấy slide bài giảng là vội kết luận niche kênh mà không đối soát với kho render thực tế và lưới video đã đăng trên kênh TikTok.

## 3. Quy tắc khắc phục & Kỷ luật bắt buộc (Remediation Discipline)

1. **Tap đúng Checkbox góc trên-phải:**
   - Trong TikTok Photo Picker, BẮT BUỘC tap vào góc trên-phải của tile:
     $$x = \text{right} - 35, \quad y = \text{top} + 35$$
     (Ví dụ trên màn 1080x1920: tọa độ `x=225, y=250`).
   - Đợi 2s để vòng tròn hiện số `1` màu đỏ và nút "Tiếp (1)" sáng lên trước khi bấm tiếp.
2. **Kỷ luật Zoom Crop vòng tròn Avatar (Chống báo cáo mù):**
   - CẤM TUYỆT ĐỐI nhìn lướt screenshot toàn màn hình hoặc tin vào `exit=0` của runner.
   - BẮT BUỘC crop riêng vùng avatar tròn (`y: 150..400, x: 400..680`) trên screenshot Profile.
   - Dùng `browser_vision` soi trực diện: xác nhận thấy rõ ngũ quan người thật (mắt, mũi, miệng) và đối chiếu với ảnh nguồn trước khi báo cáo User.
3. **Dọn sạch MediaStore trước khi Push:**
   - Tránh việc MediaStore lưu cache trỏ vào ảnh cũ, luôn purge bảng `content://media/external/images/media` và dọn các thư mục media trước khi push avatar mới.
4. **Đối soát Chủ thể Kênh với Lưới Video Profile (Chống lệch Niche):**
   - Chụp ảnh Profile TikTok, crop nửa dưới màn hình để kiểm tra lưới video bài đăng (`profile_video_grid`).
   - Kho `D:/TIKTOK-videonuoinick/<folder>/` MỚI LÀ KHO VIDEO RENDER THỰC TẾ ĐANG ĐƯỢC UPLOAD LÊN TIKTOK của tài khoản.
   - Trích xuất avatar trực tiếp từ video thực tế đang nuôi trong `D:/TIKTOK-videonuoinick/<folder>/` của chính creator xuất hiện trong các bài đăng đó; CẤM TUYỆT ĐỐI chỉ quét vài file ngẫu nhiên trong `video goc` rồi tự suy diễn chủ đề kênh.
