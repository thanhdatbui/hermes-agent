# ChatGPT Warmup Cloudflare Submit Timeout & Checkmail Triage (21/09/2026)

## 1. Hiện tượng thực tế (21/09/2026)
Trong Phase 1 chuỗi sau ca trưa (`run_all.ps1` -> `run_parallel.ps1`), Máy 55 tạo thành công Gmail `hauquynh2002woz38@gmail.com` lúc 16:10.
Ngay sau đó, tiến trình kích hoạt liên kết ChatGPT (`[WARMUP_CHATGPT]`) và bị kẹt suốt 24 phút (1.440 giây):
```text
[checkmail.live error] Page.goto: Timeout 25000ms exceeded.
Call log:
  - navigating to "https://checkmail.live/", waiting until "load"
...
[16:34:54] [WARNING] [ChatGPT-Reg] [ce051605a3d8a63903] FAIL: FAILED_AT_EMAIL_SUBMIT (EMAIL_SUBMIT_TIMEOUT, 1440.35s) - Không chuyển sang màn hình OTP sau khi submit email
[16:34:54]    ⚠ [WARMUP_CHATGPT] Dang ky ChatGPT khong thanh cong: Không chuyển sang màn hình OTP sau khi submit email
```

---

## 2. Phân tích Root Cause

### 2.1. Cloudflare Turnstile / Bot Protection trên ChatGPT Signup
- Trang đăng ký ChatGPT (`https://chatgpt.com/auth/login` hoặc màn hình signup) sử dụng Cloudflare Turnstile và Bot Protection của OpenAI.
- Khi bot điền email và click Submit, request POST bị chặn ngầm (drop hoặc silent challenge).
- Form không ném lỗi ra giao diện nhưng cũng **không chuyển hướng sang màn hình nhập OTP email**.
- Script client rơi vào vòng lặp chờ vô hạn `EMAIL_SUBMIT_TIMEOUT` kéo dài tới 1.440s (24 phút), làm trễ toàn bộ thời gian của ca chạy sau trưa.

### 2.2. Timeout dịch vụ phụ trợ `checkmail.live`
- Trước khi đăng ký, script cố gắng gọi `https://checkmail.live/` để kiểm tra trạng thái inbox hoặc live mail.
- Dịch vụ này bị timeout mạng 25s (`Timeout 25000ms exceeded`), gây delay tích lũy trên từng máy.

---

## 3. Khắc phục & Kỷ luật Fail-Fast

1. **Siết chặt Timeout Submit Email (Fail-Fast):**
   - Giới hạn cứng thời gian chờ chuyển cảnh sau khi submit email đăng ký ChatGPT từ 1.440s xuống tối đa **60–90 giây**.
   - Nếu quá 90s không thấy màn hình OTP, coi như bị bot challenge chặn ➔ abort bước ChatGPT ngay, ghi log `CHATGPT_SUBMIT_CHALLENGE_BLOCKED`, và chuyển sang các bước warm-up newsletter khác để giải phóng máy.
2. **Bọc mềm (Soft-Fail) `checkmail.live`:**
   - Đặt timeout tối đa 5-10s cho `checkmail.live`. Nếu timeout, fallback bỏ qua hoặc dùng API nội bộ thay vì block tiến trình.

---

## 4. Bẫy Ảnh Màn Đen & Thiếu Alert Telegram Khi Lỗi ChatGPT Hook (21/09/2026)
- **Hiện tượng ảnh màn đen (Black Screen):**
  - Hàm `screenshot()` trong `gmail_reg_v10.py` gọi `screencap -p /sdcard/_ss.png`. Nếu màn hình thiết bị tắt (screen sleep/dimmed) hoặc máy rơi vào sleep mode trong 24 phút timeout, `screencap` sẽ xuất ra ảnh hoàn toàn đen kịt (black image 23KB).
  - **Khắc phục:** Trước khi chụp ảnh lỗi, bắt buộc đánh thức màn hình (`prepare_device(wake=True, swipe_unlock=True)` hoặc `input keyevent 26` / `input keyevent 82`) để chụp được hiện trường UI thật của ứng dụng.
- **Thiếu Telegram Farm Alert:**
  - `hook_chatgpt_register.py` khi gặp lỗi `FAILED_AT_EMAIL_SUBMIT` chỉ gọi `screenshot()` lưu file local vào `AppData/Local/register-gmail/screenshots/`, hoàn toàn **KHÔNG gọi `send_farm_machine_alert`** (không gửi ảnh kèm banner đỏ về Telegram).
  - Muốn có cảnh báo hiện trường tức thời cho Operator, bắt buộc phải tích hợp `send_farm_machine_alert` vào các điểm nhánh lỗi trong `hook_chatgpt_register.py`.
