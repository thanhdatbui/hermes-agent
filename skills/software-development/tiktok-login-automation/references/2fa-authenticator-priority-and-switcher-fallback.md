# Quy Chuẩn Ưu Tiên 2FA Authenticator & Fallback Email OTP (2026-09-27)

## 1. Bối cảnh & Bài học thực tế từ Máy 40
- **Lỗi nhận diện**: TikTok hiển thị tiêu đề chung là *"Xác minh 2 bước"* ngay cả khi màn hình đang là form nhập OTP gửi về Email (`a***6@gmail.com`).
- **Nguy cơ chí tử**: Nếu classifier chỉ bắt từ khóa `"xac minh 2 buoc"` mà vội coi là Authenticator App, script sẽ lấy mã TOTP 6 số điền vào ô mã Email OTP -> Bị TikTok từ chối liên tiếp 3 lần dẫn tới dừng flow và tưởng nhầm nick bị sai/hỏng 2FA.

## 2. Quy tắc Ưu tiên Bất di bất dịch (User Directive)
> **LUÔN ƯU TIÊN 2FA AUTHENTICATOR TRƯỚC, OTP EMAIL SAU**

Khi gặp màn hình Xác minh 2 bước mà mặc định chìa ra luồng Email OTP:
1. **Tìm nút chuyển đổi**: Bấm vào *"Sử dụng phương thức khác"* (`Su dung phuong thuc khac` / `Use another method`).
2. **Chọn Authenticator**: Tìm và chọn *"Trình xác thực"* hoặc *"Ứng dụng xác thực"* (`Authenticator App` / `Authenticator`).
3. **Sinh & Nhập TOTP**: Lấy secret Base32 trong database sinh mã 6 số nhập vào.
4. **Fallback OTP Email**: CHỈ KHI NÀO tài khoản không có 2FA secret hoặc danh sách phương thức không có Authenticator thì mới fallback sang đọc OTP từ Gmail/Hotmail (Graph API / Outlook).

## 3. Các điểm neo UI & Nhãn chính xác
- **Nút đổi phương thức**: `"Sử dụng phương thức khác"`, `"Su dung phuong thuc khac"`, tọa độ fallback `[408, 1098]`.
- **Nhãn Authenticator**: TikTok trên Android hiện nhãn là **`Trình xác thực`** (`Trinh xac thuc`) hoặc `Ứng dụng xác thực`.
- **Màn hình Tiểu sử (Bio screen onboarding)**: Sau khi đăng nhập một số tài khoản hiện màn hình Tiểu sử (`Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào`). Bấm nút `Hủy` / `Bỏ qua` (tọa độ fallback `[95, 138]`) để vào thẳng Profile/Feed.
