# Pinned User Lock, DeviceContext & Android WebView Automation Pitfalls

## 1. Kiến trúc Pinned Device Lock (`user_authorized=True`, TTL 1h)
- **Vấn đề:** Khi operator ra lệnh chạy batch/canary thủ công, các cronjob định kỳ (feed runner, avatar watchdog) có thể thức dậy và cướp quyền điều khiển thiết bị nếu script chạy thủ công không chiếm lock hoặc chỉ dùng lock tự động (`user_authorized=False`).
- **Nguyên tắc Pinned Lock:**
  - Mọi lệnh do người dùng/operator phát động BẮT BUỘC dùng context manager `DeviceContext`:
    ```python
    from automation_core.device_lock import DeviceContext

    with DeviceContext(serial=serial, machine=str(stt), project="operator-task", user_authorized=True) as lease:
        # Toàn bộ thao tác ADB/UI trên máy được bảo vệ an toàn tuyệt đối
        ...
    ```
  - Cờ `user_authorized=True` tự động đóng dấu `pinned=True`, `ttl_seconds=3600` và `last_heartbeat` vào file lock JSON.
  - Toàn bộ cronjob và tác vụ ngầm khác gặp lock `pinned=True` sẽ lập tức bị chặn đứng (`DeviceLockNeedsUserDecision`), cấm tuyệt đối mọi hành vi takeover/preempt trừ khi có `force_preempt=True` từ chính operator.
- **Bảo toàn TTL 1h (Reaper an toàn chống deadlock qua đêm):**
  - Cronjob `reap-dead-owner-locks.py` tôn trọng TTL 1h của Pinned Lock.
  - Nếu tiến trình chủ chết (`owner_alive is False`): Thu hồi lock ngay lập tức (orphan cleanup).
  - Nếu quá 3600s (1 giờ) không còn hoạt động: Tự động chuyển sang `quarantine` với lý do `pinned_1h_ttl` để giải phóng máy, tránh treo farm qua đêm.

## 2. Các cạm bẫy khi tự động hóa Chrome & Gmail trên Samsung S7

### A. Phân biệt Server State vs Device Token State khi Check Live Gmail
- `check_gmail_is_live(email)` qua Playwright/web chỉ kiểm tra **Server State** (tài khoản có tồn tại và nhận được mail trên máy chủ Google hay không).
- Tài khoản vừa tạo trên phone farm có thể báo **LIVE** trên server nhưng bị Google Play Services đánh văng **Device Token** cục bộ (*"Đã xảy ra lỗi và bạn cần đăng nhập lại"* / *"Hoàn tất đăng nhập để tiếp tục"*).
- Khi token cục bộ bị thu hồi, app Gmail trên máy sẽ không thể tải được hòm thư cho đến khi tài khoản được re-auth hoặc re-login trên máy.

### B. Cơ chế Switch Account an toàn trong app Gmail (Tránh bốc nhầm OTP cũ)
- Trên máy có thể lưu 4–5 tài khoản Google. Không bao giờ được quét regex OTP mù quáng ngay khi mở app Gmail.
- **Quy trình chuẩn:**
  1. Mở Gmail: `am start -n com.google.android.gm/.ConversationListActivityGmail`.
  2. Tap avatar góc trên phải: `(985, 138)`.
  3. Kiểm tra Google Bento Popup:
     - Nếu `target_email` nằm trong header `og_compact_header_secondary_text`: Đã là active account $\rightarrow$ **CẤM TUYỆT ĐỐI tap vào header** (sẽ mở trang Quản lý Tài khoản Google che mất hòm thư). Chỉ cần tap ra ngoài `(540, 1800)` để đóng popup.
     - Nếu `target_email` nằm trong `og_secondary_account_information`: Tap vào node để chuyển sang nick mới. Sau đó dismiss các popup phụ (*"Không, cảm ơn"*, *"Bỏ qua"*).
  4. Bắt buộc kiểm tra tiêu đề/sender: Chỉ bóc mã khi email đến từ đúng dịch vụ mong muốn (`OpenAI`, `ChatGPT`), cấm nhặt nhầm mã xác thực cũ của TikTok/Google.

### C. Khóa cứng chiều xoay màn hình (Portrait Orientation 0)
- Nhiều máy Android trên farm có thể bị bật `accelerometer_rotation=1` và vô tình xoay ngang (`orientation=1`, 1920x1080 thay vì 1080x1920).
- Khi xoay ngang, toàn bộ tọa độ và layout của Chrome WebView bị đảo lộn, khiến script không tìm thấy ô nhập liệu hoặc tap trượt.
- **Bắt buộc khóa portrait trước khi thao tác:**
  ```python
  shell(device_id, "settings", "put", "system", "accelerometer_rotation", "0")
  shell(device_id, "settings", "put", "system", "user_rotation", "0")
  ```

### D. Chống Drift Tab trong Chrome và chặn Google SSO Bottom-Sheet
- Khi quay lại Chrome từ app khác, nếu chỉ gọi `am start -n com.android.chrome.Main`, Chrome sẽ mở lại tab foreground gần nhất (có thể là tab tìm kiếm Google cũ hoặc tab rác).
- Bắt buộc kiểm tra URL trên thanh Omnibox: Nếu không ở đúng domain đăng ký, phải điều hướng lại đúng intent URL `https://chatgpt.com/auth/login?screen_hint=signup`.
- Chrome thường tự động bật bottom-sheet *"Đã đăng nhập vào Google bằng [tài khoản cũ]"* / *"Tiếp tục với tài khoản Google"*: Phải nhận diện và tap nút Bỏ qua / Hủy / tap phía trên `(540, 300)` để tắt ngay, không để cản trở giao diện đăng ký.
