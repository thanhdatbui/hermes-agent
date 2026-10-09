# Google OAuth Recovery & reCAPTCHA Audio Solving Pitfalls in Playwright

## 1. Google Account Recovery Challenge ("Choose how you want to sign in")

### Triệu chứng & Bẫy selector
- Google hiển thị nhiều lựa chọn xác minh:
  1. `Get a verification code at <recovery-email>` (thường bị khóa: `Unavailable because of too many attempts. Please try again later.`)
  2. `Confirm your recovery email` (yêu cầu gõ lại toàn bộ email khôi phục).
- **Cạm bẫy vòng lặp vô tận (Loop Trap):**
  - Nếu script tìm text `'Confirm your recovery email'` trên toàn bộ thẻ (`div, span, li`), nó sẽ match trúng tiêu đề hoặc container của trang.
  - Khi script click vào container đó rồi `continue`, nó sẽ lặp lại vô tận mà **không bao giờ** chạm tới khối kiểm tra và điền ô input email (`input[name="knowledgePreregisteredEmailResponse"]` / `input[type="email"]`).

### Chuẩn hóa thứ tự xử lý (Input-First Rule)
1. **Kiểm tra input form trước:** Quét `input[name="knowledgePreregisteredEmailResponse"], input[type="email"], input[id*="recovery"]`. Nếu tìm thấy và hiển thị, điền `recovery_email` (hoặc fallback email cấu hình), kích hoạt sự kiện `input`/`change`, nhấn Enter và click Next.
2. **Chỉ click chọn phương thức khi chưa có input form:**
   - Thu hẹp selector vào thẻ lựa chọn thực sự: `[data-challengeindex], [data-challengetype], li, [role="link"], [role="button"]`.
   - Tuyệt đối loại trừ các option có chứa `Unavailable because of too many attempts` hoặc `aria-disabled="true"`.

---

## 2. reCAPTCHA Audio Solver Pitfall (Pointer Intercept Crash)

### Triệu chứng & Nguyên nhân
- Khi popup câu đố hình ảnh (`bframe`) đã tự động mở hoặc bung ra sẵn, việc gọi `anchor_btn.first.click(timeout=5000)` vào `#recaptcha-anchor` (checkbox "I'm not a robot") sẽ bị overlay của popup che khuất (`<div> subtree intercepts pointer events`).
- Playwright sẽ thử lại 5 giây rồi văng `TimeoutError: Locator.click: Timeout 5000ms exceeded`.
- **Hậu quả:** Nếu lệnh click anchor nằm chung trong khối `try...except` với toàn bộ logic giải audio, ngoại lệ này sẽ làm ngắt toàn bộ hàm giải captcha, khiến script văng `return False` trước khi kịp tìm `bframe` và nút audio (`#recaptcha-audio-button`).

### Chuẩn hóa cấu trúc hàm giải Audio
1. **Kiểm tra sự tồn tại của `bframe` trước:** Nếu `bframe` đã có trong `page.frames`, lập tức bỏ qua click anchor checkbox.
2. **Cách ly lỗi click anchor:** Bọc riêng lệnh click anchor trong `try...except` cục bộ với `force=True` và timeout ngắn (2-3s) để nếu bị overlay che pointer events thì bỏ qua, trôi tiếp xuống tìm nút audio.
3. **Thao tác nút Audio an toàn:** Dùng `audio_btn.first.click(timeout=5000, force=True)` hoặc `audio_btn.evaluate("el => el.click()")` để tránh bị overlay chặn tương tự.
