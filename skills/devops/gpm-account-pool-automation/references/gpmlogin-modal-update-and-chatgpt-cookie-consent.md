# GPMLogin Modal "Big Update" Fake Error, Cookie Banner & OAuth Account Chooser Signed-Out Handling

## 1. GPMLogin Modal "Big Update" Fake Error (`Yêu cầu cập trình duyệt [Chromium] [142]`)
### Triệu chứng & Bản chất
- Khi gọi GPM Local API `GET /api/v3/profiles/start/{id}`, API trả về:
  ```json
  {"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
  ```
- **Bản chất thực tế:** Không phải profile thiếu core Chromium 142 hay browser hỏng, mà là ứng dụng GPMLogin đang hiển thị một **Modal Dialog toàn màn hình (ví dụ: thông báo "Big Update", release notes)**. Khi modal này mở, toàn bộ engine backend của GPMLogin chuyển sang trạng thái chờ tương tác người dùng và trả về mã lỗi giả để ép người dùng bấm nút trên UI.
- **Xử lý triệt để:**
  1. **Bấm đóng modal:** Gửi lệnh click UI vào nút đỏ "Đóng thông báo" (ví dụ qua Win32 click tại tọa độ tâm nút).
  2. **Chặn hiển thị vĩnh viễn:** Cập nhật file cấu hình phiên bản thông báo của GPMLogin:
     ```python
     with open(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\do_not_show_what_news', 'w') as f:
         f.write('4.3.6-stable') # hoặc phiên bản hiện tại của app
     ```
  3. **Chụp ảnh màn hình GPM bị kẹt (Elevated/Admin session) không dùng Desktop Handle:**
     - Khi GPM chạy quyền Elevated hoặc background agent không truy cập được màn hình qua `CopyFromScreen` ("The handle is invalid") hoặc thiếu `PIL._imaging`:
     - Dùng PowerShell biên dịch C# gọi `PrintWindow(hwnd, hdc, 2)` (flag `PW_RENDERFULLCONTENT`) để chụp trọn vẹn cửa sổ GPM lưu ra PNG trực tiếp làm bằng chứng visual.
  4. **Quy tắc bất biến:** Tuyệt đối KHÔNG tự ý bypass GPM API để mở Playwright `launch_persistent_context` trực tiếp, vì sẽ mất anti-detect engine của GPMLogin và kích hoạt ngay rào chắn `v3/signin/rejected` của Google SSO.

---

## 2. Watchdog Báo Cáo Gọn & Silent Mode
- Khi viết/sửa watchdog cronjob (như `cron_chatgpt_web_pool_watchdog.py`):
  - Tuyệt đối KHÔNG in danh sách thô dài dòng hay log từng thao tác mở profile lên kênh chat.
  - Định dạng chuẩn: 1 dòng tóm tắt ngắn gọn trạng thái pool (Active/Total, số lượng cần chú ý).
  - Silent Invariant: Nếu pool đạt 100% Active hoặc không có lỗi mới phát sinh, watchdog phải im lặng (exit không gửi thông báo) để tránh spam người dùng.

---

## 2. ChatGPT Web Cookie Banner Overlay (`Tùy chọn cookie` / Cookie Consent)
### Triệu chứng
- Khi Playwright mở `https://chatgpt.com/`, trang web hiển thị một banner cookie overlay che khuất toàn bộ màn hình (`data-octane-static-cookie-consent`).
- Khi cố click vào nút "Đăng nhập" / "Log in", Playwright báo lỗi:
  ```text
  TimeoutError: <a ... data-cookie-preferences-link="">Tùy chọn cookie</a> intercepts pointer events
  ```
- Hoặc nút "Tiếp tục với Google" trên `/auth/login` không kích hoạt được vì sự kiện click bị nuốt bởi overlay.

### Xử lý chuẩn
Trước khi thực hiện bất kỳ thao tác click đăng nhập nào trên ChatGPT Web:
```python
# 1. Chấp nhận Cookie Consent nếu xuất hiện
accept_btn = page.locator('button:has-text("Chấp nhận tất cả"), button:has-text("Accept all"), button:has-text("Allow all")').first
if accept_btn.count() > 0 and accept_btn.is_visible():
    accept_btn.click()
    time.sleep(1.5)

# 2. Sau đó mới click nút Đăng nhập / Continue with Google
```

---

## 3. Google OAuth Account Chooser Trạng Thái "Đã đăng xuất" (Signed Out)
### Triệu chứng
- Tại màn hình Google Account Chooser (`accounts.google.com/v3/signin/accountchooser`):
  - Hiển thị danh sách tài khoản, nhưng bên cạnh email có nhãn xám: **`Đã đăng xuất` (Signed out)**.
  - Khi click vào tài khoản đó, Google không chuyển thẳng vào OAuth consent mà điều hướng sang màn hình yêu cầu mật khẩu (`v3/signin/challenge/pwd`).
- **Phân biệt:**
  - **LIVE SSO:** Tài khoản đang giữ session active -> Click là sang màn hình Consent cấp token trong 3-5 giây.
  - **Signed out:** Cookie session Google đã hết hạn -> Cần quy trình đăng nhập lại mật khẩu (password challenge), không thể bypass tự động bằng 1 click. Script cần bắt URL `challenge/pwd` để đánh dấu acc cần re-login thay vì timeout.
