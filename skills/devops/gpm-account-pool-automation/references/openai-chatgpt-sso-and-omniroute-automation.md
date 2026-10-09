# OpenAI / ChatGPT SSO Automation & OmniRoute Pool Integration

Tài liệu đúc kết từ thực chiến tự động hóa đăng nhập ChatGPT qua Google SSO trên GPMLogin, phân biệt bản chất giữa `codex` vs `chatgpt-web`, xử lý form Onboarding đa ngôn ngữ và bảo vệ tài nguyên máy tính.

---

## 1. Phân biệt Bản chất: Codex vs ChatGPT-Web trên OmniRoute (:20129)

| Đặc tính | Codex (`codex`) | ChatGPT-Web (`chatgpt-web`) |
| :--- | :--- | :--- |
| **Bản chất Token** | OAuth Developer Token (`accessToken` + `refreshToken`) hoặc session CLI | Cookie Web Session (`__Secure-next-auth.session-token`) |
| **Model hỗ trợ** | `gpt-5.6-sol`, `gpt-5.6-terra-high`, `gpt-5.5`, `codex/*` | Hỗ trợ TOÀN BỘ: `gpt-5.6-luna`, `gpt-5.6-sol-high/xhigh`, `gpt-5.6-terra-high` |
| **Hạn ngạch (Quota)** | Quota riêng của Developer API. Khi cạn sẽ văng `503 Unavailable (reset after 700h)`. Không nên dồn nhiều request vào 1 acc đơn lẻ. | Quota giao diện Web thông thường. **Không bị chung hạn ngạch với Codex**. Reset ngắn hạn theo ngày/giờ. |
| **Quy trình lấy Token** | Gọi `/api/oauth/codex/start-callback-server` -> duyệt OAuth URL -> dễ dính checkpoint Verify Phone của OpenAI. | Bấm `Continue with Google` trên `chatgpt.com/auth/login` -> lấy cookie `session-token` -> nạp vào `POST /api/providers`. |

> **Bằng chứng thực nghiệm**: Cùng một tài khoản `voha`, `ngongan`, `buitrang`, `lamhien`, `luuhuong`: khi gọi qua Codex dính `503 (reset after 699h)`, nhưng gọi qua `chatgpt-web` vẫn trả về `200 OK` trơn tru!

---

## 2. Các cạm bẫy Onboarding "About You" & Cách khắc phục triệt để

Khi tài khoản Google lần đầu liên kết ChatGPT, OpenAI chuyển hướng tới `https://auth.openai.com/about-you`.

### Pitfall 1: Lỗi kẹt DateField Tiếng Việt (Năm 2026) - NGUY HIỂM NHẤT
- **Triệu chứng**: Giao diện tiếng Việt hiển thị 3 ô Ngày / Tháng / Năm riêng biệt (`div[data-type="day"]`, `month`, `year`). Mặc định khởi tạo lấy ngày hiện tại (năm `2026`).
- **Hậu quả**: Nếu không xóa năm `2026`, tuổi người dùng = 0 (dưới 13 tuổi) -> OpenAI báo lỗi đỏ: *"Chúng tôi không thể tạo tài khoản với thông tin đó. Vui lòng thử lại"* và văng `token_exchange_failed`!
- **Giải pháp chuẩn**:
  ```python
  # Phải dùng Control+A để bôi đen và ghi đè giá trị
  day_el = page.locator('div[data-type="day"]').first
  if day_el.count() > 0 and day_el.is_visible():
      day_el.click()
      page.keyboard.press("Control+A")
      page.keyboard.type(f"{random.randint(10, 28):02d}", delay=80)

      month_el = page.locator('div[data-type="month"]').first
      month_el.click()
      page.keyboard.press("Control+A")
      page.keyboard.type(f"{random.randint(1, 12):02d}", delay=80)

      year_el = page.locator('div[data-type="year"]').first
      year_el.click()
      page.keyboard.press("Control+A")
      page.keyboard.type(str(random.randint(1996, 2002)), delay=80) # Đảm bảo 24-30 tuổi
  ```

### Pitfall 2: Input Age Tiếng Anh bị intercept pointer events
- **Triệu chứng**: Tag `<label>` đè lên input khiến `age_inp.click()` timeout 30s.
- **Giải pháp**: Dùng `age_inp.click(force=True)` -> `page.keyboard.press("Control+A")` -> `page.keyboard.type(str(age))`.

---

## 3. Quy tắc kiểm chứng nghiệm thu (Verification Gate)

- **Không tin vào cookie trần**: Truy cập `https://chatgpt.com/` kiểm tra số lượng nút `Đăng nhập` / `Log in`.
  - Nếu số nút đăng nhập = 0: **Đã đăng nhập thật sự**.
  - Nếu màn hình vẫn còn nút "Đăng nhập" / "Đăng ký miễn phí": Cookie bốc được chỉ là **guest / anon token**, gọi test sẽ fail hoặc không lưu context.
- **Nghiệm thu ảnh Gate 6**: Luôn chụp screenshot màn hình chính khi đã vào New Chat hoặc có profile button/avatar.

---

## 4. Kỷ luật dọn dẹp tiến trình GPM (Chống tràn Taskbar)

Khi chạy batch nhiều luồng (`worker = 3` hoặc `5`):
- Khi `GPM API /api/v3/profiles/stop/{id}` phản hồi, các tiến trình con `chrome.exe` của GPM Browser có thể không tắt hẳn mà trở thành process mồ côi (treo taskbar hàng trăm cửa sổ).
- **Quy tắc dọn dẹp bắt buộc trong block `finally`**:
  ```python
  def cleanup_gpm_profile(profile_id, profile_path):
      try:
          requests.get(f"http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}", timeout=5)
      except Exception:
          pass
      if profile_path:
          for p in psutil.process_iter(['name', 'exe', 'cmdline']):
              try:
                  exe = p.info.get('exe') or ''
                  cmd = ' '.join(p.info.get('cmdline') or [])
                  # Chỉ diệt chrome.exe của gpm_browser, CẤM đụng xiaowei / phone farm
                  if 'chrome.exe' in p.info.get('name', '').lower() and 'gpm_browser' in exe.lower():
                      if profile_path in cmd:
                          p.kill()
              except Exception:
                  pass
  ```
