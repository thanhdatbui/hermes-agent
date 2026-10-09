# Google Glif Sign-in reCAPTCHA Multi-Step & Phone IAP Checkpoint Handling

## 1. reCAPTCHA Multi-step Glif Flow trên Profile Mới
Khi đăng nhập tài khoản trên profile GPM sạch (Core 142) mới tạo:
1. Nhập Email $\rightarrow$ Bấm `#identifierNext`.
2. Google có thể hiện thông báo trung gian *"Xác nhận bạn không phải là rô-bốt"* trên URL `v3/signin/identifier` trước khi render iframe captcha.
3. Click nút *"Tiếp theo"* để chuyển hướng sang URL `https://accounts.google.com/v3/signin/challenge/recaptcha`.
4. Tại URL `challenge/recaptcha`:
   - Tìm iframe `enterprise/anchor` $\rightarrow$ Click `#recaptcha-anchor`.
   - Tìm iframe `enterprise/bframe` $\rightarrow$ Click `#recaptcha-audio-button`.
   - Tải file MP3, convert WAV qua `pydub` + `ffmpeg-8.1.2`, nhận diện bằng `speech_recognition.Recognizer().recognize_google()`.
   - Điền kết quả vào `#audio-response` $\rightarrow$ Click `#recaptcha-verify-button`.
   - **BƯỚC BẮT BUỘC TIẾP THEO:** Sau khi giải xong captcha, kiểm tra và click lại nút *"Tiếp theo"* / *"Next"* trên trang chính để Google chuyển tiếp sang trang nhập mật khẩu `v3/signin/challenge/pwd`.

## 2. Pitfall CẤM KỴ: Bấm "Thử cách khác" (Try another way) trên trang reCAPTCHA
- **Lỗi nghiêm trọng:** Nếu script bấm *"Thử cách khác"* khi đang ở trang `challenge/recaptcha`, Google sẽ coi đó là hành vi từ chối xác thực bot và chuyển hướng ngay lập tức sang `https://accounts.google.com/v3/signin/rejected` (Hard Reject) $\rightarrow$ Đăng nhập thất bại.
- **Quy tắc:** Tuyệt đối KHÔNG bấm *"Thử cách khác"* khi URL đang chứa `challenge/recaptcha` hoặc khi khung captcha chưa được giải.

## 3. Phone SMS Checkpoint (IAP Challenge) & Fail-Closed Protocol
Khi Google nghi ngờ tài khoản bị đổi IP / đăng nhập bất thường:
- URL chuyển sang `https://accounts.google.com/v3/signin/challenge/iap` hoặc nội dung *"Có điều bất thường về hoạt động của bạn... Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh"*.
- Thao tác click *"Thử cách khác"* trên màn hình này vẫn trả về duy nhất yêu cầu số điện thoại SMS (không có tùy chọn recovery email hay mã bảo mật 10 số).
- **Quy trình xử lý chuẩn:**
  1. Ghi nhận tài khoản dính `Google Phone SMS Checkpoint (IAP)`.
  2. Đóng profile browser context và dừng profile GPM ngay lập tức.
  3. Xóa profile tạm khỏi GPMLogin bằng API `delete_profile(profile_id, mode=2)` để không để lại rác trong `GroupId=1`.
  4. Cập nhật trạng thái `DIE` kèm ghi chú chi tiết `Google Login Failed: Google Phone SMS Checkpoint (IAP) | Clean Profile Deleted` vào `master_gmail_manager.xlsx`.

## 4. Android Device Lock Preemption (`force_preempt=True`)
Khi gọi hàm `automation_core.device_lock.acquire_device_lock`:
- Các phiên trước bị gián đoạn hoặc crash có thể để lại lock file trong `~/.codex/device-locks/`.
- Luôn truyền `force_preempt=True` và `bypass_proxy_readiness=True` khi thực hiện các tác vụ can thiệp UI S7 lấy mã bảo mật để dọn dẹp các dead locks an toàn mà không bị văng lỗi `DeviceLockUnavailable`.
