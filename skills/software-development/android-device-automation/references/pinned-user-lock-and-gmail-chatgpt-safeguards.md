# Pinned User Lock & Gmail ChatGPT Automation Safeguards (2026-09-20)

## 1. Pinned User Lock Architecture & 1h TTL Safety
- **Core Principle:** Mọi script thao tác thiết bị do User trực tiếp chỉ đạo (Canary, manual batch, emergency recovery) BẮT BUỘC phải dùng `DeviceContext(serial=serial, machine=str(stt), project=..., user_authorized=True)`.
- **Pinned Schema:**
  - `user_authorized=True` tự động đóng dấu `pinned=True`, `last_heartbeat`, và `ttl_seconds=3600` vào payload `machine_<N>.lock.json` và `serial_<S>.lock.json`.
  - **Miễn nhiễm cướp quyền (Preempt Immunity):** Mọi cronjob nền (TikTok feed runner, upload avatar watchdog, sync adapter) khi quét thấy `pinned=True` sẽ bị ném `DeviceLockNeedsUserDecision` hoặc từ chối takeover (`SAME_PROJECT_RECOVERY` / `FULL_SCOPE_TAKEOVER` bị chặn đứng).
  - Duy nhất cờ `force_preempt=True` (`OPERATOR_PREEMPT`) mới được phép reclaim.
- **Bảo toàn TTL 1h (Reaper Safety):**
  - Khóa Pinned Lock được bảo vệ tối đa 1 giờ (`3600s`).
  - Reaper (`reap-dead-owner-locks.py`, chạy mỗi 5 phút) xử lý an toàn:
    1. Nếu tiến trình chủ chết (`owner_alive is False`): Thu hồi lock ngay, không để lại zombie lock.
    2. Nếu tiến trình còn sống hoặc không rõ nhưng `age_seconds >= 3600`: Tự động di chuyển vào `quarantine` với lý do `pinned_1h_ttl`, triệt tiêu nguy cơ farm bị kẹt cứng deadlock qua đêm.

## 2. Gmail App Switch Account Pitfalls (Google Bento Popup)
- **Cơ chế Switch Account:**
  - Khi mở app Gmail (`com.google.android.gm`), máy thường có sẵn nhiều tài khoản Google từ các ca trước.
  - Bắt buộc kiểm tra `target_email` có đang active không. Nếu chưa, tap avatar góc trên phải (`985, 138` trên S7 1080x1920) để mở Google Bento Account Popup.
- **TỬ HUYỆT BENTO POPUP (Active Account Header):**
  - Trong Bento Popup, tài khoản ĐANG ACTIVE hiển thị ở header `resource-id="com.google.android.gm:id/og_compact_header_secondary_text"`.
  - CẤM TUYỆT ĐỐI tap vào email này nếu nó đã là active account! Việc tap vào active header sẽ khiến Google mở trang *"Quản lý Tài khoản Google"* (màn hình có chữ X, Chính sách riêng tư...), che khuất hoàn toàn hòm thư và làm script timeout.
  - Chỉ tap vào email mục tiêu khi nó nằm trong danh sách tài khoản phụ (`resource-id="com.google.android.gm:id/og_secondary_account_information"`).
  - Sau khi switch, tự động dismiss các dialog phụ: *"Duyệt web an toàn"*, *"Không, cảm ơn"*, *"Bỏ qua"*.

## 3. Chrome Multi-Tab Drift Prevention
- **Hiện tượng Drift Tab:**
  - Khi switch giữa Chrome và Gmail (để lấy OTP), nếu dùng intent `com.android.chrome/com.google.android.apps.chrome.Main` mà không truyền URL, Chrome sẽ phục hồi tab foreground gần nhất (có thể là tab tìm kiếm Google rác cũ, ví dụ search `408g`...).
  - Dẫn đến việc script tap mù tọa độ `(540, 1100)` trúng ngay trang tìm kiếm Google thay vì ô nhập mã OTP.
- **Giải pháp:**
  - Ở đầu Step 3, sau khi mang Chrome lên foreground, đọc UI XML kiểm tra URL:
  - Nếu URL là `google.com` hoặc không chứa `chatgpt.com` / `openai.com`: Bắt buộc tái kích hoạt Intent với URI đích:
    `am start -a android.intent.action.VIEW -d "https://chatgpt.com/auth/login?screen_hint=signup" com.android.chrome`
- **Bộ lọc OTP chuẩn:**
  - Tuyệt đối chỉ trích xuất mã OTP khi tiêu đề hoặc XML xác nhận đúng là từ **`OpenAI`** hoặc **`ChatGPT`**.
  - Cấm regex bốc mã 6 số mù quáng vì sẽ nhặt nhầm mã OTP cũ của TikTok hoặc Google Antigravity.
