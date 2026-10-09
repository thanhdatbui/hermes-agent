# Pinned User Lock & 1-Hour TTL Safety Architecture (2026-09-19)

## 1. Vấn Đề Gốc Rễ
- Khi Operator/User ra lệnh chạy script ad-hoc (Canary, Batch link ChatGPT, test sửa lỗi), nếu script chỉ gọi ADB trực tiếp hoặc dùng lock lỏng lẻo:
  + Các cronjob định kỳ của farm (feed runner, avatar watchdog, sync ca tối) quét thấy máy không có lock hoặc cố takeover lock -> Cướp quyền điều khiển thiết bị, đè app khác lên foreground khiến tác vụ của Operator thất bại.
- Nếu thiết kế User Lock "miễn nhiễm hoàn toàn" không có thời hạn:
  + Khi agent bị crash, OOM, mất mạng, hoặc máy host khởi động lại qua đêm -> Trở thành "zombie lock" vĩnh viễn, sáng hôm sau toàn bộ farm bị kẹt cứng (deadlock).

## 2. Kiến Trúc Giải Pháp: Pinned Lock + 1h TTL Guard

### A. Tầng Lock (`automation_core.device_lock`):
1. Khi `user_authorized=True` (lệnh từ User / Canary / Batch):
   - Payload lock file tự động được gắn:
     ```json
     {
       "user_authorized": true,
       "pinned": true,
       "last_heartbeat": "2026-09-19T...",
       "ttl_seconds": 3600
     }
     ```
2. **Chặn Đứng Preempt Thường:**
   - Mọi caller tự động (`user_authorized=False`) gặp Pinned Lock sẽ raise `DeviceLockNeedsUserDecision`.
   - Các scope takeover ngầm (`SAME_PROJECT_RECOVERY`, `FULL_SCOPE_TAKEOVER`) bị từ chối thẳng thừng.
   - CHỈ DUY NHẤT lệnh có `force_preempt=True` (`TAKEOVER_SCOPE_OPERATOR_PREEMPT`) mới được quyền reclaim.
3. **Context Manager Chuẩn:**
   ```python
   from automation_core.device_lock import DeviceContext
   
   with DeviceContext(serial=serial, machine=str(stt), project="operator-task", user_authorized=True) as lease:
       # Thao tác độc quyền trên thiết bị
       ...
   # Tự động giải phóng lock an toàn khi thoát
   ```

### B. Tầng Dọn Dẹp Tự Động (`reap-dead-owner-locks.py`):
- Tuân thủ trần TTL 1 giờ (`LOCK_TTL_SECONDS = 3600`):
  1. Nếu tiến trình chủ đã chết (`owner_alive is False`): Reap ngay lập tức sang `quarantine`, không để lại zombie lock.
  2. Nếu tiến trình còn sống nhưng `age_seconds >= 3600`: Reap với lý do `pinned_1h_ttl` để giải phóng máy, chống deadlock qua đêm.
  3. Nếu `age_seconds < 3600`: Giữ nguyên (bảo vệ tuyệt đối cho Operator trong vòng 1 giờ).

## 3. Bài Học Về ChatGPT Link & Gmail Multi-Account Trên S7:
1. **Chrome WebView Input Hint:**
   - Ô nhập email trên Chrome WebView có thể để trống `text` và `content-desc`, nhưng nhãn lại nằm ở thuộc tính `hint="Email address"` với `resource-id="email"`.
   - Khi tìm element, parser bắt buộc phải kiểm tra cả `attrs.get("hint")`.
2. **Tránh Chạm Omnibox URL Của Chrome:**
   - Vùng Omnibox URL của Chrome trên Samsung S7 chiếm Y=60..220.
   - Khi cần tap ẩn bàn phím ảo an toàn, tuyệt đối không tap vào Y<300. Dùng tọa độ an toàn `(540, 600)` (vùng giữa màn hình / khoảng trống) thay vì `(540, 200)`.
3. **Gmail Multi-Account OTP Fetch:**
   - Thiết bị farm thường lưu nhiều tài khoản Google cũ. Khi mở Gmail để lấy OTP, bắt buộc phải kiểm tra xem app Gmail có đang mở đúng hòm thư của nick cần lấy OTP hay không.
   - Nếu đang hiển thị nick khác: Bắt buộc tap avatar (`985, 138`) -> switch sang đúng nick mục tiêu -> kiểm tra đúng thư từ `OpenAI` / `ChatGPT` mới được bóc mã, tránh bốc nhầm mã OTP của các app khác (TikTok, Google) lưu từ trước.
