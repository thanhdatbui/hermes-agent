# Pinned Device Lock, 1h TTL Safety & ChatGPT Gmail Automation Pitfalls

## 1. Pinned Device Lock & 1h TTL Safety Pattern
- **Bối cảnh:** Các lệnh của User (Canary, batch test, chạy thủ công) chạy trên farm Android thường bị các cronjob tự động (TikTok feed, upload avatar, sync) can thiệp, cướp quyền foreground do không có lock hoặc chỉ dùng lock tự động thông thường.
- **Quy tắc bất biến:**
  1. Mọi lệnh/script tương tác thiết bị do User chỉ đạo **BẮT BUỘC** phải chiếm lock qua `DeviceContext` hoặc `acquire_device_lock(user_authorized=True)`.
  2. Khi `user_authorized=True`: Lock file tự động gắn cờ `pinned=True`, ghi `last_heartbeat` và `ttl_seconds=3600`.
  3. Mọi cronjob tự động (`user_authorized=False`) hoặc cơ chế takeover thường khi gặp lock có `pinned=True` sẽ lập tức bị chặn lại (`DeviceLockNeedsUserDecision` hoặc từ chối takeover). Chỉ duy nhất `force_preempt=True` (chính tay User override) mới được phép cướp quyền.
  4. **Bảo toàn TTL 1h:** Giữ nguyên cơ chế tự động dọn dẹp sau 1 giờ (`LOCK_TTL_SECONDS = 3600`) qua reaper cronjob (`reap-dead-owner-locks.py`). Nếu tiến trình sở hữu đã chết (`owner_alive is False`), thu hồi ngay; nếu quá 1 giờ không có phản hồi, thu hồi lock sang `quarantine` với lý do `pinned_1h_ttl` để tránh zombie lock gây deadlock cho các ca nuôi sau.

## 2. ChatGPT On-Device Registration: Chrome Tab-Drift & Bento Popup Pitfalls
- **Cấm gọi intent Chrome không URL ở Step 3:**
  - Tuyệt đối không dùng `am start -n com.android.chrome/com.google.android.apps.chrome.Main` khi quay lại Chrome từ Gmail, vì Chrome sẽ restore tab foreground gần nhất (thường là tab tìm kiếm Google rác cũ).
  - Phải kiểm tra URL: nếu phát hiện rơi vào `google.com` hoặc tab rác, lập tức kích hoạt lại intent chứa đúng link đăng ký: `am start -a android.intent.action.VIEW -d "https://chatgpt.com/auth/login?screen_hint=signup" com.android.chrome`.
- **Cơ chế Switch Account trong Gmail Bento Popup:**
  - Khi mở Gmail để lấy OTP, app có thể đang đứng ở tài khoản cũ. Bắt buộc kiểm tra avatar góc trên phải (`985, 138`) để switch account sang `target_email`.
  - **Tử huyệt Bento Popup:** Trong popup tài khoản của Google, tài khoản đang active nằm ở header `og_compact_header_secondary_text`. CẤM TUYỆT ĐỐI tap vào node này vì sẽ mở trang *"Quản lý Tài khoản Google"*, che khuất hòm thư. Chỉ tap vào `target_email` khi nó nằm ở node tài khoản phụ (`og_secondary_account_information`). Nếu đã là active header, chỉ cần tap ra ngoài đóng popup.
  - **Lọc chính xác OTP:** Chỉ trích xuất mã OTP khi tiêu đề hoặc nội dung email xác nhận đúng là từ `OpenAI` hoặc `ChatGPT`. Cấm quét regex 6 chữ số mù quáng trên toàn màn hình Gmail vì sẽ bốc nhầm mã OTP cũ của TikTok hoặc Google.
