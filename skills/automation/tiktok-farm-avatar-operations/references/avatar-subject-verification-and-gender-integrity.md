# Avatar Subject Verification & Cross-Niche Gender Integrity

## Bối Cảnh Sự Cố & Bài Học
Khi vận hành đổi avatar đơn lẻ hoặc batch trên TikTok farm, việc phát sinh các avatar rác (logo, watermark) hoặc sai giới tính (gán ảnh nam cho nick nữ và ngược lại) bắt nguồn từ 3 bẫy kỹ thuật chính:

---

### 1. Bẫy False Face Detection trên Video Slide / Infographic
- **Hiện tượng:** Trên các kênh thuộc chủ đề *Học tập, Sức khỏe, Đời sống, Kiến thức*, video gốc thường là slide đồ họa, bài giảng, infographic y khoa (ví dụ: sơ đồ não, sỏi thận) kèm watermark/logo góc trên (ví dụ: huy hiệu GDĐT, logo kênh).
- **Nguyên nhân:** Bộ lọc Haar Cascade hoặc detector cơ bản rất dễ bắt nhầm hình vẽ tròn, biểu tượng ngọn đuốc, quả địa cầu hoặc đồ họa giải phẫu thành "khuôn mặt người". Khi tự động crop theo bounding box này, avatar tạo ra là logo/watermark rác chứ không phải con người.
- **Quy tắc bắt buộc:**
  1. Tuyệt đối không crop mù theo tọa độ Haar detector trên các folder infographic/slide.
  2. Bắt buộc kiểm tra loại video: nếu kênh là slide/kiến thức không có người quay mặt thật (human on-camera), **CẤM** cố trích xuất frame từ video đó làm avatar. Phải điều hướng sang kho creator tương ứng hoặc lấy từ folder cùng phân khúc nhân vật.

---

### 2. Bẫy Ảo Giác Giới Tính (Gender Hallucination Trap)
- **Hiện tượng:** Agent tự tiện lấy file avatar có sẵn từ các folder máy khác (ví dụ: `m10`, `m5` thuộc kênh Gym/Fitness nam giới) rồi tự thêu dệt mô tả thành "bạn nữ áo len trắng, tóc dài dịu dàng", dẫn đến việc gửi ảnh nam thanh niên cơ bắp, xăm trổ cho tài khoản nữ tính (`Kieu Lam`).
- **Nguyên nhân:** Agent nhìn thoáng hoặc suy diễn theo mong muốn (confirmation bias) thay vì đọc từng chi tiết của ảnh qua vision/OCR.
- **Quy tắc nghiệm thu giới tính:**
  1. Khi tài khoản yêu cầu avatar nữ (tên nick nữ, nội dung nữ tính): **BẮT BUỘC** tra cứu các folder thuộc đúng niche nữ (`Làm đẹp`, `Thời trang`, `Makeup`, `Phụ nữ` trong workbook `Tik*.xlsx`).
  2. Khi gọi `browser_vision`, câu hỏi kiểm tra **BẮT BUỘC PHẢI KHÁCH QUAN VÀ TRỰC DIỆN**:
     - *"Chủ thể trong ảnh là nam hay nữ? Tóc ngắn hay dài? Có râu, hình xăm, hay cơ bắp không? Mặc trang phục gì?"*
     - Cấm mớm cung hoặc đặt câu hỏi gợi ý dạng *"Có phải bạn nữ áo hồng không?"*.
  3. Tuyệt đối không được gửi ảnh cho User khi chưa xác nhận 100% giới tính thực tế qua vision độc lập.

---

### 3. Checkpoint Trực Quan & Tránh False-Positive Runner
- Trước khi thực hiện lệnh upload lên thiết bị, **BẮT BUỘC** gửi ảnh thành phẩm (Square 512x512 + Circular crop preview) cho User xác nhận hoặc lưu artifact nghiệm thu rõ ràng.
- Trên thiết bị TikTok Android:
  - Tọa độ checkbox chọn ảnh trong Photo Picker (4 cột, 1080x1920) nằm ở góc trên bên phải tile: `(225, 250)`, không tap vào tâm `(137, 355)`.
  - Nút "Tiếp" tại `(920, 1855)` chỉ có hiệu lực khi checkbox đã hiện tick số đỏ `(1)`.
  - Cảnh giác bẫy nút "Lưu" ở đáy màn hình "Sửa hồ sơ" `(792, 1794)`: Không được nhầm lẫn màn hình "Sửa hồ sơ" với màn hình Crop avatar thực tế.
