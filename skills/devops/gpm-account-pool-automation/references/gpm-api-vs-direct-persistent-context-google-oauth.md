# Bài học vận hành & Pitfalls: GPMLogin API vs Launch Persistent Context Trực Tiếp (Google OAuth SSO)

## 1. Bản chất cơ chế Anti-Detect của GPMLogin
- GPMLogin không chỉ là một launcher lưu trữ thư mục `user_data_dir`. Khi gọi API `http://127.0.0.1:19995/api/v3/profiles/start/{id}`:
  - Tiến trình `GPMLogin.exe` và `gpmdriver.exe` sẽ tiêm (inject) các native hook C++/DLL (`gpmdriver.exe`, hooking WebGL, Audio, Canvas, Navigator, sửa đổi fingerprint và che giấu hoàn toàn flag `navigator.webdriver` ở tầng sâu nhị phân).
  - Sau đó Playwright chỉ đóng vai trò kết nối qua Chrome DevTools Protocol (`pw.chromium.connect_over_cdp(f"http://{addr}")`).
  - Nhờ cơ chế này, khi thực hiện SSO "Continue with Google" (vào OpenAI ChatGPT, Anthropic, v.v.), Google nhận diện đây là trình duyệt người dùng thật (100% pass OAuth Consent & Chooser).

## 2. Thất bại cấu trúc: Tự ý bypass API GPM bằng `launch_persistent_context`
- **Hiện tượng lỗi:** Khi API GPM bị nghẽn/chặn (ví dụ lỗi `Yêu cầu cập trình duyệt [Chromium] [142]`), nếu Coordinator/Worker tự ý chuyển sang dùng Playwright `launch_persistent_context` trỏ thẳng vào folder profile (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<path>`) và file binary `chrome.exe`:
  - Dù có bật `headless: True` hay `False`, truyền `--disable-blink-features=AutomationControlled`, bỏ `--enable-automation`, hay tiêm script giả lập `navigator.webdriver = undefined`:
  - Google Identity Service (Accounts Google) **phát hiện môi trường automation ngay lập tức** tại bước chọn tài khoản OAuth Chooser.
  - Kết quả: Trình duyệt bị redirect sang `https://accounts.google.com/v3/signin/rejected` với thông báo chặn:
    > *"Không thể đăng nhập cho bạn. Trình duyệt hoặc ứng dụng này có thể không an toàn. Hãy thử dùng trình duyệt khác."*

## 3. Lỗi chặn `Yêu cầu cập trình duyệt [Chromium] [XXX]` trên GPMLogin
- **Nguyên nhân:**
  - App `GPMLogin` quản lý trạng thái tải/xác nhận browser core thông qua cấu hình nội bộ và giao diện WPF.
  - Khi một profile được gán core Chromium mới (ví dụ Core 142 hoặc 127) mà app chưa hoàn tất bước xác nhận tải trên GUI, API `/api/v3/profiles/start/{id}` sẽ từ chối khởi động và trả về JSON:
    `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}`
- **Quy tắc xử lý:**
  - **CẤM TUYỆT ĐỐI** tự ý đổi architecture sang `launch_persistent_context` trực tiếp để "chữa cháy", vì sẽ làm cháy tài khoản hoặc bị Google đánh gậy bot-detection `rejected`.
  - Phải duy trì luồng chuẩn: Báo người dùng hoặc tự động kích hoạt cập nhật core qua giao diện app GPMLogin (Click tab *Quản lý Profiles* / *Cài đặt* -> Bấm *Cập nhật trình duyệt*).
  - Khi API trả về HTTP 200 và cấp `remote_debugging_address`, Playwright mới được kết nối qua CDP.
