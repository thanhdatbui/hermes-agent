# Kỷ Luật Dữ Liệu & Vận Hành Reg Gmail

## 1. Cấm Tuyệt Đối Đoán Mò Mật Khẩu Điền Excel
- Khi script chạy đơn lẻ hoặc không lưu password vào file, TUYỆT ĐỐI CẤM Coordinator tự tính toán template `build_password()` để đoán mò pass rồi điền vào Excel.
- Không có pass trong log thực tế từ biến runtime: Báo thẳng thất bại/mất pass và gỡ tài khoản khỏi máy, không bịa pass.

## 2. Cooldown Reg Gmail Farm >= 4 Ngày
- Máy vừa reg thành công BẮT BUỘC nghỉ tối thiểu 4 ngày. Cấm chọn lại máy vừa reg cùng ngày hoặc < 4 ngày.
- Pick batch nhiều máy bắt buộc gom các máy có Mobile Proxy khác nhau, không chạy chung cổng proxy.
- Cấm đổi IP trước khi reg.

## 3. Cơ Chế Fresh Account Security Delay Của Google
- Tài khoản mới tạo trên thiết bị di động bị Google khóa quyền truy cập tính năng Bảo mật cấp cao (Xác minh 2 bước / 2FA) trong vòng vài giờ đến 24 giờ đầu.
- Nhập pass ở màn hình 2SV sẽ bị loop xác minh danh tính. Cần ngâm tài khoản tối thiểu 24h trước khi kích hoạt 2FA.
