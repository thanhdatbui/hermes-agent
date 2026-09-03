# Pull-to-Refresh Verification in Follow Runner (19/08/2026)

## Quy tắc Vuốt Xác Nhận Follow Không Bị Nhả
- **Hiện tượng**: TikTok có cơ chế nhả follow tự động sau vài giây đối với các tài khoản bị rate-limit hoặc tương tác bất thường.
- **Yêu cầu**: Sau khi tap nút Follow, script bắt buộc phải reload lại trang Profile để kiểm tra nút có giữ nguyên trạng thái "Đang theo dõi / Nhắn tin" hay quay trở lại nút "Follow" màu đỏ.
- **Hướng vuốt chuẩn xác**:
  - Động tác reload trang trên ứng dụng TikTok di động là **kéo từ trên xuống (Pull-to-refresh)**.
  - Toạ độ chuẩn: Điểm bắt đầu $y_1 = \frac{1}{3}h$ (khoảng $y=600$ trên màn 1080x1920) ➔ Điểm kết thúc $y_2 = \frac{4}{5}h$ (khoảng $y=1500$), $x = \frac{1}{2}w$, thời gian $400..600$ms.
  - **TUYỆT ĐỐI KHÔNG dùng vuốt từ dưới lên (swipe up)** vì swipe up chỉ cuộn danh sách video xuống dưới chứ không kích hoạt hiệu ứng tải lại dữ liệu trang cá nhân.
- **Triển khai code**: Đã bổ sung hàm `pull_to_refresh_profile(adapter)` trong `adapter.py` và tích hợp vào `verify_follow.py::_confirm_not_released()`.
