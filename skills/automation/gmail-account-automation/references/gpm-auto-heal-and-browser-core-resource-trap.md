# GPMLogin Background Auto-Heal & Browser Core Resource Trap

## 1. GPMLogin Background Auto-Heal (Không cần mở app thủ công)
- **Tình trạng:** Sau khi máy tính reboot hoặc GPMLogin bị tắt, cổng API v3 (`127.0.0.1:19995`) sẽ bị từ chối kết nối (`WinError 10061`).
- **Cơ chế tự phục hồi (Auto-heal):**
  - File thực thi: `%LOCALAPPDATA%\Programs\GPMLogin\GPMLogin.exe`.
  - Có thể kích hoạt nền thông qua Python `subprocess.Popen([str(exe)])`.
  - Cổng API `19995` sẽ online trở lại sau 1-3 giây (`Microsoft-HTTPAPI/2.0`).
  - **Quy tắc điều phối:** TUYỆT ĐỐI KHÔNG bắt người dùng phải "bật app GPM bằng tay" khi API chưa sống. Agent hoàn toàn có thể tự spawn tiến trình nền này.

## 2. Bẫy Lỗi Tài Nguyên Core Trình Duyệt: "Yêu cầu cập trình duyệt [Chromium] [X]"
- **Triệu chứng:**
  - API list profiles và quản lý nhóm vẫn trả về `HTTP 200 OK`.
  - Khi gọi `GET /api/v3/profiles/start/{profile_id}`, API trả về:
    ```json
    {"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
    ```
- **Căn nguyên kỹ thuật:**
  - Trong thư mục `gpm_browser/gpm_browser_chromium_core_142`, các file nhị phân `chrome.exe`, `gpmdriver.exe`, `chrome.dll` vẫn tồn tại đầy đủ.
  - Tuy nhiên, bên trong logic của GPMLogin app, khi app vừa khởi động lại hoặc có bản cập nhật Fingerprint / resource manifest mới trên server GPM, app sẽ khóa quyền kích hoạt `gpmdriver.exe` qua Local REST API cho đến khi gói tài nguyên được xác thực.
- **Hành vi API:**
  - Không thể downgrade profile về version cũ hơn (ví dụ: `Do not downgrade from version 137`).
  - Tạo profile mới với core cũ (ví dụ 139) cũng bị chặn với thông báo tương tự (`Yêu cầu cập trình duyệt [Chromium] [139]`).
- **Cách giải quyết:**
  1. **Giải pháp triệt để trên GPM:** Người dùng hoặc nhân viên vận hành cần bấm nút **"Cập nhật lại GPM"** (hoặc xác nhận cập nhật gói tài nguyên Chromium) trực tiếp trên giao diện WPF của GPMLogin. Ngay khi bấm xong, server GPM đồng bộ xong thì API `profiles/start` sẽ lập tức trả về `success: true`.
  2. **Giải pháp thay thế tức thì (Fallback O(1)):** Nếu đang cần tương tác tự động gấp (như điền form, kiểm tra web), dùng trực tiếp **Chrome chính của hệ thống kèm cổng CDP** (Skill `logged-in-chrome-cdp-marketplace`), không phụ thuộc vào trạng thái tài nguyên của GPMLogin.
