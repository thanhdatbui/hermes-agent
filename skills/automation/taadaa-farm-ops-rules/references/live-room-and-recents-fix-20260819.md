# Bản Ghi Tối Ưu Tỉ Lệ Tương Tác & Tự Động Giải Cứu Phòng Live / Popup Trống Recents (19/08)

## 1. Cân Bằng Tỉ Lệ Tương Tác Feed (Trust Score Anti-Bot)
- **Tỉ lệ Like Feed**: Giảm từ 12% xuống **`4%`** trên For You, `3%` trên Following, `2%` trên Friends.
- **Tỉ lệ Follow trực tiếp từ Feed**: Giảm từ 6% xuống **`1%`** (Tài khoản chỉ follow có chọn lọc, luồng follow chính qua Mode 1 tìm kiếm profile bên `tiktok-follow`).
- **Tổng lượng video / ca**: 
  - Mỗi phiên lướt: `15 - 30` video (trung bình ~22 video).
  - 1 Ca (3 phiên): `45 - 90` video (trung bình ~68 video/nick) — đạt chuẩn vàng Trust Score người dùng thật.

## 2. Tự Động Thoát Phòng Live (Live Room Escape)
- **Hiện tượng (Máy 49)**: Lướt trúng phòng Live TikTok có `2.0K` người xem, bình luận chạy liên tục, bị nhận diện nhầm thành `startup ad/splash`.
- **Cơ chế xử lý**:
  - Mở rộng bộ lọc `live_room_exit` trong `feed_swipe_smoke.py`: Nhận diện tất cả các text `Phòng...`, `Bảng xếp hạng...`, icon đóng `X` (`id/close`, `id/e63`, `id/e6n`, `id/e68`).
  - Dừng xem tự nhiên 3–6s rồi tự động bấm nút đóng `X` / vuốt thoát về lại Feed chính.

## 3. Xử Lý Màn Hình Recent Apps Trống Lúc Khởi Động (Máy 8)
- **Hiện tượng**: Máy 8 đã ở Home sạch sẽ, bấm Recent Apps (187) không có nút "Đóng tất cả", code `automation_core.startup.prepare_app_for_automation` cũ coi đây là lỗi nghiêm trọng làm dừng máy.
- **Xử lý**:
  - Cập nhật `automation_core/startup.py`: Nếu không thấy nút đóng do recents rỗng, coi như ứng dụng đã sạch và tiếp tục mở app bình thường.
  - Cài đặt bản editable `pip install -e D:/Taadaa/automation-core` vào venv farm.
