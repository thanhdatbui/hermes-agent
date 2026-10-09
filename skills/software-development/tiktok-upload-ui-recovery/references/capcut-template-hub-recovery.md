# CapCut Template Preview & Creation Hub UI Recovery in TikTok Upload

## 1. Triệu chứng & Hiện trường
- Khi script mở camera để tải video (`VIDEO_PICK`), TikTok mở ra ở chế độ `LIVE` hoặc camera mặc định.
- Thao tác chuyển tab từ `LIVE` hoặc vuốt cạnh vô tình chạm trúng tab **`MẪU` (Templates / CapCut Hub)**.
- Màn hình bị kẹt ở **Template Preview** (`Thử mẫu này` / `Use this template`, bài hát/video mẫu) hoặc **Creation Hub** (`Video mới`, `Mẫu`, `AutoCut`, `Trình chỉnh sửa ảnh`, `Phụ đề`, `AI Self`, `Tách nền`).
- Dẫn đến timeout tại `VIDEO_PICK` và văng lỗi `upload_subprocess_nonzero`.

## 2. Giải pháp Phòng ngừa (Preventive Guard)
- Khi chuyển chế độ từ `LIVE` sang quay thường:
  - BẮT BUỘC target chính xác text/bounds của `ĐĂNG`, `TẠO`, `15 giây`, `60 giây`, `Máy ảnh`.
  - Tuyệt đối không dùng tọa độ vuốt biên trượt lấn sang vùng chứa tab `MẪU` / `Templates`.
  - Ưu tiên tap trực tiếp vào icon **Upload Thumbnail** (`view_bg2`, `upload_hot_area`, `cwr`, hoặc visual fallback góc phải dưới `(0.875 * W, 0.83 * H)`) thay vì gạt tab camera.

## 3. Giải pháp Khôi phục Đa tầng (Multi-step Auto-Dismiss)
- Nhận diện Template Preview: `Thử mẫu này`, `Use this template`, `Bởi CapCut`, `id/use_template`.
- Nhận diện Creation Hub: `Video mới`, `Mẫu`, `AutoCut`, `Trình chỉnh sửa ảnh`, `Phụ đề`, `AI Self`, `Tách nền`.
- Thoát màn hình đa tầng:
  1. Quét và tap nút back top-left `<` (`id/bq3`) hoặc nút `Đóng` (`id/h32` / `content-desc="Đóng"`).
  2. Kết hợp fallback phím `BACK` có giới hạn (`max_attempts=4`) để chuyển tiếp từ Preview -> Hub -> Camera/Feed.
  3. Sau khi dismiss thành công, kiểm tra lại UI camera và gọi lại cơ chế mở picker.
