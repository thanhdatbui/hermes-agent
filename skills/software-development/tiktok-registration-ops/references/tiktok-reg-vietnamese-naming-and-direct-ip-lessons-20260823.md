# TikTok Reg Lessons Learned & Proxy Verification Patterns (2026-08-23)

## 1. Quy tắc Đặt Tên Hiển Thị Tiếng Việt (User Rule)
- Sau khi đăng ký thành công, nếu TikTok chuyển sang màn "Tạo tên / Đặt biệt danh" (Nickname screen), **BẮT BUỘC** nhập tên tiếng Việt có nghĩa (viết hoa chữ đầu, tra từ mapping tên Việt `_VI_NAME_MAP` hoặc fallback qua `_VI_NAME_FALLBACK`).
- Tuyệt đối không đặt tên tiếng Anh hoặc chuỗi vô nghĩa ngẫu nhiên khi đã có quy tắc tên tiếng Việt.

## 2. Phân Biệt OTP Đăng Ký vs OTP Đăng Nhập
- **Màn OTP Đăng Nhập (Login):** Có nút xanh *"Đăng nhập bằng mật khẩu"* phía dưới các ô nhập mã OTP.
  - Sự xuất hiện của màn này KHÔNG ĐỒNG NGHĨA email chắc chắn đã có tài khoản TikTok.
  - Khi người dùng kiểm tra qua luồng Reset Password ("Đặt lại bằng email"), nếu TikTok báo *"Địa chỉ email chưa được đăng ký"*, tức là email thực tế **CHƯA TỪNG ĐĂNG KÝ**.
  - Script cần vào đúng luồng Đăng ký (Sign Up) thay vì gõ nhầm ở màn hình Đăng nhập rồi báo sai trạng thái.

## 3. Hiện Tượng Kẹt OTP / Xoay Loading Do Trùng Direct IP Farm
- **Triệu chứng:** Nhập đúng mã OTP xong nhưng màn hình TikTok xoay loading mãi không chuyển sang bước tiếp theo (DOB/Password/Profile).
- **Nguyên nhân gốc rễ:** 
  - Proxy bị sập hoặc dùng proxy nội bộ (`mirotik1.taadaa.click:1000x`) không đổi IP WAN ra ngoài $\rightarrow$ thiết bị đi ra bằng Direct IP gốc của farm (`1.53.114.53`).
  - TikTok cho phép 1 máy đầu tiên đăng ký thành công theo quota, nhưng các máy sau dùng chung IP này sẽ bị server-side rate limit / throttle ở bước xác thực OTP.
- **Xử lý:**
  1. Kiểm tra live IP ViChanger xem có trùng với Host Public IP không.
  2. Đổi proxy sang dải 4G sạch (`test.taadaa.click:51xx`).
  3. Để IP farm nguội 2-3 ngày trước khi chạy lại batch reg trên các máy đó.
