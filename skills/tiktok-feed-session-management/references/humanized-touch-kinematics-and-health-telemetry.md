# Humanized Touch Kinematics & Pragmatic Account Health Telemetry

## 1. Cải tiến Vuốt Ngón Tay (Humanized Finger Swipe)
Trong `python_runner/flows/feed_swipe_smoke.py`, lệnh swipe cơ học cũ có các nhược điểm:
- `DEFAULT_SWIPE_DURATION_MS = 650` (550ms – 750ms): Tốc độ vuốt quá lì, thiếu tính dứt khoát của người dùng thật trên short-video feeds.
- Điểm vuốt tuyến tính dọc thẳng đứng với độ lệch hẹp (`-18..+12px`) tạo mẫu máy móc dễ bị phân tích chuyển động (Touch Dynamics / Acceleration Profile).

### Thiết kế chuẩn hóa (Kinematics Parameters):
- **Tốc độ vuốt dứt khoát (Duration):** Điều chỉnh về dải `220ms – 420ms` (tự nhiên cho thao tác lướt TikTok nhanh).
- **Góc nghiêng tự nhiên ngón cái (Thumb Arc Drift):**
  - Điểm đặt ngón cái `start_x`: ngẫu nhiên trong vùng `[470, 520]`.
  - Độ lệch khi lướt lên đỉnh `end_x`: drift nghiêng tự nhiên từ `-35px` đến `+15px` (mô phỏng quẹt ngón tay thuận chéo nhẹ lên góc trên bên trái).
  - Clamp an toàn: Bắt buộc giữ `[450, 540]` để không chạm mép màn hình, không trúng các nút chức năng cạnh phải hoặc thanh tìm kiếm.
  - Thời gian nhấc tay nghỉ ngẫu nhiên (`post_swipe`): `0.6s – 1.8s`.

---

## 2. Telemetry Sức Khỏe Tài Khoản Thực Chiến (Pragmatic Health Telemetry)

### ⚠️ Pitfall: Chống Over-Engineering Giám Sát Phần Cứng
- **Bài học từ phản hồi thực tế của User:** Trong môi trường phone farm cày cuốc (box farm quạt tản nhiệt chạy 24/7), điện thoại nóng là hiện tượng bình thường. TUYỆT ĐỐI KHÔNG tự ý đưa các logic kiểm tra nhiệt độ pin/CPU vào để bóp quota, hạ limit hay dừng máy làm gián đoạn sản lượng farm.
- Không suy diễn quá đà từ lý thuyết sang các cơ chế rườm rà.

### Bộ Chỉ Số Tinh Gọn (Zero-Cost Signals):
1. **View Video Đăng (Upload Yield):**
   - Đọc trực tiếp số view trên lưới video lúc vào Profile Preflight (đã có XML/OCR).
   - Phát hiện tình trạng **0-View Jail** sau 24h đăng.
2. **Tỷ lệ Follow Nhả (Unfollow Drop Rate):**
   - Tận dụng dữ liệu từ `verify_follow.py` (cơ chế pull-to-refresh kiểm tra nút đổi về "Follow" đỏ).

### Ma Trận Xử Lý 2 Cấp Độ:
- **Bình Thường (Healthy / Normal Flop):** View > 0, follow giữ tốt $\rightarrow$ Giữ nguyên 100% công suất cày.
- **Phạt Nặng (Shadowban / 0-View Jail 2 ca liên tiếp hoặc nhả follow hàng loạt):**
  - Tự động chuyển nick sang **Deep Organic Rest (Nghỉ cày 3 ngày)**: Chỉ lướt feed thuần, 0 upload, 0 follow để phục hồi trust.
  - Không bóp ngắt máy lẻ tẻ làm gãy lịch trình cron.
