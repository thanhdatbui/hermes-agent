# Cấm Tuyệt Đối Xoay Ngang Màn Hình & Chuỗi Đổi Hotmail Sau TikTok 2FA (18/09/2026)

## 1. Cấm Tuyệt Đối Xoay Ngang Màn Hình (Orientation Invariant)
- **Cấm tiệt đối:** Khi thao tác UI automation trên thiết bị Samsung S7 (kể cả mở trình duyệt Chrome, app Outlook hay TikTok), CẤM TUYỆT ĐỐI để màn hình xoay ngang (Landscape).
- **Lý do:** Màn hình ngang làm gãy toàn bộ UI layout, lệch toàn bộ tọa độ tap định sẵn, che mất bàn phím và làm Operator cực kỳ bức xúc.
- **Lệnh enforce bắt buộc trước và trong khi chạy:**
  ```bash
  content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
  content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
  ```
- Nếu phát hiện màn hình có nguy cơ xoay ngang (hoặc chụp ảnh kích thước `width > height`), lập tức chạy 2 lệnh trên để ép về $1080 \times 1920$ dọc ngay.

---

## 2. Bỏ Hoàn Toàn Bước Gỡ Email Khỏi 2FA TikTok
- Từ 18/09/2026, luồng TikTok Add 2FA **bỏ vĩnh viễn bước gọi `disable_email_and_confirm_stable()`**.
- Nick TikTok no-phone không thể tắt hoàn toàn phương thức email ở tầng server-side mà không bị dính toast lỗi bảo mật: *"Không thể thay đổi cài đặt vì lý do bảo mật, hãy thử lại sau"*.
- Chỉ cần xác nhận: `Trình xác thực (TOTP): Bật` + `Mật khẩu: Bật` là hoàn thành 100% mục tiêu 2FA cho nick.

---

## 3. Quy Trình Chuỗi Đổi Info Hotmail Đã Reg TikTok
Chỉ chạy đổi thông tin Hotmail cho các tài khoản **CHƯA TỪNG CHANGE**:

### A. Nhận diện Hotmail Chưa Từng Change (Idempotency):
- Quét log audit `.ai-runs/hotmail-change-info/` hoặc state tracker.
- Đối soát mật khẩu Cột G Excel (`PASS_MAIL`): nếu còn mang định dạng ngắn/mặc định của bên bán (vd: `10.09...`, `hpvze263500`, `G1WIEF63`...) thì là CHƯA CHANGE. Nếu đã là pass random mạnh của farm thì BỎ QUA.

### B. Luồng thực thi chuẩn:
1. **Bước 1 — Gọi Script Đổi Info trên Chrome:**
   - Mở Chrome trên đúng máy S7 đó (qua Proxy của máy).
   - Đăng nhập Hotmail bằng pass cũ.
   - Đổi sang mật khẩu ngẫu nhiên mạnh mới (`generate_account_password` 14-16 ký tự).
   - Gỡ email khôi phục tạm của bên bán (nếu có).
   - Bấm **"Đăng xuất khỏi mọi thiết bị" (Sign out everywhere)** để thu hồi toàn bộ token cũ và đá văng phiên bên bán.
   - Ghi mật khẩu mới vào Cột G Excel.
2. **Bước 2 — Mở App Outlook trên Máy S7:**
   - Mở app Outlook ở chế độ màn hình dọc cố định.
   - Đăng nhập bằng Email + Mật khẩu mới vừa đổi.
   - Hoàn tất đăng nhập vào Hộp thư đến để giữ phiên sạch chính chủ.
