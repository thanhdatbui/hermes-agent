# Quy tắc Device Lock Farm Taadaa

## 1. Nguyên tắc cốt lõi
- Khóa thiết bị (`DEVICE_LOCK_ENABLED=1`) là cơ chế bảo vệ phân định quyền điều khiển giữa các tiến trình tự động và can thiệp thủ công.
- **Chỉ mở khóa (Unlock) khi:**
  1. Tiến trình đạt trạng thái **SUCCESS** hoàn tất (xác nhận profile, ghi nhận workbook/tracking, dọn dẹp app về Home).
  2. Hoặc khi **User trực tiếp ra lệnh** mở khóa.
- **Tuyệt đối CẤM:** Tự động mở khóa hàng loạt khi tiến trình thất bại, đang kẹt màn hình lỗi hoặc chưa có chỉ thị từ người vận hành.
