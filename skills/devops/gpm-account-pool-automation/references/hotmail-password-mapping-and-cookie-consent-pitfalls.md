# Hotmail Password Mapping & Cookie Consent Pitfalls (2026-10-10)

## 1. Bẫy Suy Diễn Sai "Shop Bán Sai Pass / Nick Đã Bị Đổi Pass"
- **Hiện tượng:** Tài khoản Hotmail đã reg thành công TikTok (nhận OTP ngon lành trên thiết bị), nhưng khi supervisor tự động đăng nhập Hotmail trên GPMLogin để reg ChatGPT hoặc nạp pool thì Microsoft báo đỏ: *"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"*.
- **Sai lầm tai hại của Agent:** Vội vàng kết luận "shop bán sai pass", "nick đã từng bị đổi pass", hoặc "hết hạn bảo hành 24h" mà không kiểm tra dữ liệu nội bộ.
- **Root Cause cốt lõi trong code:**
  1. Trong `batch_gpm_5profiles_supervisor.py` hàm `load_state`, khi profile đã có sẵn trong state JSON, lệnh update loại trừ các trường password:
     ```python
     profiles[key].update({k: v for k, v in account.items() if k not in {"password", "mail_password", "chatgpt_password"}})
     ```
     Dẫn đến việc nếu ban đầu `mail_password` bị rỗng (hoặc nạp thiếu), state sẽ vĩnh viễn không bao giờ được cập nhật lại từ Excel.
  2. Tại hàm `execute`, lệnh chạy script login Hotmail có fallback tai hại:
     ```python
     "--password", info.get("mail_password") or info.get("password") or ""
     ```
     Trong hệ thống Taadaa, trường `password` là cột `PASS` (mật khẩu TikTok của nick), còn mật khẩu Hotmail nằm ở cột `PASS MAIL`. Khi `mail_password` rỗng, script tự động lấy mật khẩu TikTok đem đăng nhập vào Microsoft Live.
  3. **Kết quả:** Microsoft báo sai pass 100%, nick bị đày vào Cooldown 48h oan uổng dù mật khẩu trong Excel vẫn đúng.
- **Quy tắc phòng ngừa bất biến:**
  - Luôn đồng bộ `mail_password` từ cột `PASS MAIL` vào state nếu Excel có dữ liệu.
  - CẤM TUYỆT ĐỐI fallback sang trường `password` TikTok khi đăng nhập Hotmail. Nếu thiếu `mail_password` phải fail-closed báo thiếu dữ liệu để kiểm tra Excel, không được lấy pass của dịch vụ khác gõ bừa vào Microsoft.

## 2. Bẫy Microsoft Cookie Consent Banner
- **Hiện tượng:** Sau khi submit mật khẩu Hotmail đúng, Microsoft chuyển hướng qua `auth/complete-client-signin-oauth-silent` và bật modal/banner Cookie Consent: *"Chúng tôi dùng cookie tùy chọn để cải thiện trải nghiệm của bạn... [Chấp nhận] [Từ chối]"*.
- Nếu script không click banner này, trang web bị dừng lại ở URL chuyển hướng hoặc landing ban đầu, khiến detector nhận nhầm là tài khoản bị kẹt/BLOCKED.
- **Xử lý chuẩn:**
  - Quét và click ngay các selector của cookie banner:
    ```python
    cookie_selectors = [
        "button:has-text('Accept')", "button:has-text('Chấp nhận')",
        "input[value='Accept']", "input[value='Chấp nhận']",
        "#acceptButton", "#onetrust-accept-btn-handler",
        "button[id*='accept']", "button[id*='Accept']",
        "button:has-text('Từ chối')", "button:has-text('Decline')",
    ]
    ```
  - Chờ trang hoàn tất chuyển tiếp sang `https://account.microsoft.com/account` rồi mới chụp ảnh Post-submit và xác nhận `LOGIN SUCCESS`.

## 3. Đồng Bộ `last_result` Khi Cứu Hộ Profile
- Báo cáo định kỳ (Lifecycle 6h) kiểm tra lỗi qua cả `info.get("status")` và `info.get("last_result", {}).get("status")`.
- Khi can thiệp cứu hộ một profile từ FAILED/BLOCKED sang PENDING/COMPLETED, bắt buộc phải làm sạch hoặc cập nhật `last_result` sang `COMPLETED`, tránh việc profile đã chạy xong nhưng báo cáo 6h vẫn đếm nhầm vào danh sách "CẦN XỬ LÝ".
