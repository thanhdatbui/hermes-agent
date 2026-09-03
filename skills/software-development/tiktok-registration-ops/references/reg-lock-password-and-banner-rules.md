# Quy tắc Vận hành Đăng ký TikTok (Tiktok_Reg Rules)

## 1. Khóa máy (Device Lock Policy)
- **Chỉ nhả lock khi thành công:** Máy chỉ được giải phóng lock khi đăng ký thành công và đã ghi nhận tracking an toàn (`VERIFIED_SUCCESS`).
- **Giữ lock khi thất bại:** Bất kỳ máy nào thất bại, timeout, hoặc bị dừng giữa chừng BẮT BUỘC phải giữ lock ở trạng thái `blocked` (hoặc `handoff`) để bảo vệ hiện trường, cấm tự động nhả lock khiến các script khác can thiệp chéo.

## 2. Xử lý Mật khẩu TikTok (Password Policy)
- **Không qua màn nhập pass:** Nếu đăng ký theo flow OTP / email-only mà TikTok không hiển thị màn hình tạo mật khẩu -> BẮT BUỘC để TRỐNG (`None`) ở cột PASS TikTok trong file Excel `taikhoan_dat_v2_updated .xlsx`. Tuyệt đối KHÔNG được tự ý gán mật khẩu ngẫu nhiên để sau này có thể vào TikTok cài đặt mật khẩu thủ công/bổ sung.
- **Có qua màn nhập pass:** Chỉ khi tài khoản thực sự đi qua bước nhập và xác nhận password trên giao diện TikTok thì mới lưu mật khẩu đó vào workbook.

## 3. Quy chuẩn Báo cáo & Hình ảnh Lỗi
- **Ảnh báo lỗi kèm Banner Đỏ:** Mọi ảnh chụp màn hình gửi báo cáo cho user khi có máy lỗi/dừng phiên BẮT BUỘC phải được chèn banner đỏ ở đầu ảnh ghi rõ `[MAY XX] - HH:MM DD/MM` theo đúng quy chuẩn của `automation_core.alerts.send_farm_machine_alert()`.
- **Ngôn ngữ báo cáo:** Báo cáo bằng tiếng Việt súc tích, ngắn gọn, nêu rõ số máy và nguyên nhân chính, tránh xả log tiếng Anh dài dòng gây rối.
