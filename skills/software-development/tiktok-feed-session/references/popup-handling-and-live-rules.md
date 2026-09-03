# Quy tắc Xử lý Popup, Modal & Màn hình lạ (Cập nhật 19/08/2026)

## 1. Phân tầng xử lý Popup (2 tầng bắt buộc)

### Tầng 1: Automation-Core (`automation-core`) — TẮT NGAY LẬP TỨC
- **Đối tượng:** Mọi popup/hộp thoại cấp hệ điều hành Android / hệ thống:
  - Quyền vị trí (`Cho phép TikTok truy cập vị trí của thiết bị này?`) $\rightarrow$ Tick *"Không hỏi lại"* + bấm *"TỪ CHỐI"*.
  - Quyền danh bạ (`Cho phép TikTok truy cập vào danh bạ của bạn?`) $\rightarrow$ Tick *"Không hỏi lại"* + bấm *"TỪ CHỐI"*.
  - Cảnh báo PackageInstaller, Google Play Services, thông báo Vi Changer VPN...
- **Quy tắc:** Xử lý tức thì (< 0.5s) để giải phóng màn hình và không làm mất focus của TikTok.
- **Whitelist Package hệ thống:** Khi kiểm tra focus sau close, cho phép `com.google.android.packageinstaller`, `com.android.packageinstaller`, `com.android.permissioncontroller`, `com.android.systemui` để tránh báo lỗi mất focus giả.

### Tầng 2: In-App Feed Repo (`tiktok-luot nuoi acc`) — CHỜ VÀI GIÂY MỚI THOÁT
- **Đối tượng:** Mọi popup/modal/màn hình xuất hiện bên trong TikTok:
  - **Phòng Live (`live_room_exit`):** Dừng xem ngẫu nhiên **6.0 – 14.0 giây** rồi bấm nút `✕` góc trên bên phải (`id/close`, `id/e63`, `id/e6n`, tọa độ góc phải $y < 300$).
  - **Trang TikTok Shop / Chi tiết SP (`shop_product_detail_close`):** Dừng xem chi tiết / giá **3.0 – 7.0 giây** rồi bấm nút `✕` (`id/gnl`, `id/e5w`).
  - **Bảng "Bài đăng lại" (`repost_sheet_close`):** Dừng **2.0 – 4.0 giây** rồi bấm nút `✕` (`id/e55`).
  - **Banner CTA quảng cáo ("Mua ngay", "Tìm hiểu thêm", "Xem ngay", "Cài đặt ngay", "Tải ngay"):** Tự động swipe lướt qua.
- **Mục đích:** Mô phỏng chính xác hành vi người dùng thật, tránh telemetry phản xạ máy móc.

## 2. Cơ chế Fallback 2 Lớp cho Popup lạ / Không rõ
1. **Lớp 1 (Detector):** Khớp các quy tắc định danh cụ thể trong danh sách rule.
2. **Lớp 2 (Swipe Recovery Fallback):** Nếu gặp popup/dialog lạ chưa định danh hoặc CTA không qua được $\rightarrow$ Tự động thử **swipe lướt qua tối đa 2 lần (`_swipe_recovery_on_stuck`)** để cố thoát màn hình về Feed trước khi kết luận manual-needed.

## 3. Tọa độ vuốt an toàn lướt Feed
- **Trục X:** Cố định tại dải an toàn **$X = 450$px** (nửa trái màn hình).
- **Trục Y:** $1540 \rightarrow 620$px.
- **Lý do:** Tránh hoàn toàn việc ngón tay chạm trúng cụm nút tương tác bên phải ($X > 600$: avatar follow, tim, comment, lưu, đĩa nhạc) và thanh bình luận/repost ở đáy ($Y > 1750$).

## 4. Dọn dẹp Recent Apps khi rỗng
- Khi vào màn hình Recent Apps và thấy text *"Không có ứng dụng đã dùng gần đây"* hoặc *"Không có ứng dụng"* $\rightarrow$ Coi là nền sạch và bấm `Home` tiếp tục phiên chạy, không báo lỗi thiếu nút Clear All.
