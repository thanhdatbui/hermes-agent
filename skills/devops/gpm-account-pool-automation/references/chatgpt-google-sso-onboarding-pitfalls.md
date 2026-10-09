# ChatGPT Web / OpenAI SSO Automation Pitfalls & Solutions on GPM Profiles

Tài liệu đúc kết thực chiến khi tự động hóa đăng nhập ChatGPT qua Google SSO trên GPM Profiles và nạp token vào OmniRoute (port 20129).

---

## 1. Cấu trúc Onboarding "About You" (Bẫy Ngày Sinh / Năm Mặc Định)
- **Triệu chứng**: Form `auth.openai.com/about-you` bị lỗi `Chúng tôi không thể tạo tài khoản với thông tin đó` hoặc redirect về `error?payload=... (errorCode: token_exchange_failed)`.
- **Nguyên nhân cốt lõi**:
  - Giao diện tiếng Anh: chỉ có 1 ô `input[name="age"]`.
  - Giao diện tiếng Việt: dùng component `react-aria-DateField` gồm 3 ô riêng biệt: `div[data-type="day"]`, `div[data-type="month"]`, `div[data-type="year"]`. Component này **mặc định gán năm hiện tại của máy tính** (ví dụ: `2026`).
  - Nếu không xóa sạch số `2026`, tài khoản bị tính là 0 tuổi (< 13 tuổi theo quy định COPPA/OpenAI), hệ thống từ chối tạo tài khoản và chặn vĩnh viễn request đó.
- **Giải pháp xử lý bắt buộc**:
  ```python
  # 1. Dạng ô Age (tiếng Anh)
  age_inp = page.locator('input[name="age"]').first
  if age_inp.count() > 0 and age_inp.is_visible():
      age_inp.click(force=True)
      page.keyboard.press("Control+A")
      page.keyboard.type(str(random.randint(22, 28)), delay=80)

  # 2. Dạng DateField 3 ô (tiếng Việt) - BẮT BUỘC Control+A xóa số mặc định
  day_el = page.locator('div[data-type="day"]').first
  if day_el.count() > 0 and day_el.is_visible():
      day_el.click()
      page.keyboard.press("Control+A")
      page.keyboard.type(f"{random.randint(10, 28):02d}", delay=80)

      month_el = page.locator('div[data-type="month"]').first
      if month_el.count() > 0:
          month_el.click()
          page.keyboard.press("Control+A")
          page.keyboard.type(f"{random.randint(1, 12):02d}", delay=80)

      year_el = page.locator('div[data-type="year"]').first
      if year_el.count() > 0:
          year_el.click()
          page.keyboard.press("Control+A")
          page.keyboard.type(str(random.randint(1996, 2002)), delay=80) # 24 - 30 tuổi hợp lệ
  ```

---

## 2. Phân Biệt Session Token Thật vs Token Khách (Guest / Anonymous Token)
- **Triệu chứng**: Script báo lấy được cookie `__Secure-next-auth.session-token` và nạp thành công vào OmniRoute (test trả về 200 OK), nhưng khi mở trình duyệt lên thì ChatGPT vẫn hiện nút "Đăng nhập" / "Đăng ký miễn phí" (chưa đăng nhập thật).
- **Cơ chế nhận diện**:
  - **Token đăng nhập chính thức (Authenticated)**: Bắt đầu bằng `eyJhbG...` (chuỗi JWT mã hóa thông tin tài khoản Google).
  - **Token khách (Guest / Anonymous)**: Bắt đầu bằng các tiền tố khác hoặc không chứa thông tin user khi decode.
- **Quy tắc nghiệm thu Gate 6**: BẮT BUỘC kiểm tra trên màn hình ChatGPT:
  ```python
  # Phải đảm bảo không còn nút Đăng nhập / Log in trên màn hình
  login_btns_count = page.locator('button:has-text("Log in"), button:has-text("Đăng nhập")').count()
  assert login_btns_count == 0, "Chưa đăng nhập thật, chỉ là guest session!"
  ```

---

## 3. Lỗi OpenAI `token_exchange_failed` & Rate-Limit WAF
- **Lỗi**: `https://auth.openai.com/error?payload=...` -> decode payload ra:
  ```json
  {"kind": "AuthApiFailure", "errorCode": "token_exchange_failed"}
  ```
  hoặc `https://chatgpt.com/auth/error?error=undefined` ("Oops! We ran into an issue").
- **Nguyên nhân**:
  - Chạy đồng thời quá nhiều worker (ví dụ: 5 workers) dồn request qua cùng một gateway/dải IP MobiProxy khiến hệ thống Cloudflare WAF của OpenAI kích hoạt phòng vệ.
- **Kỷ luật khắc phục**:
  - Giới hạn tối đa **2–3 workers song song** cho tác vụ auth ChatGPT.
  - Thêm độ trễ ngẫu nhiên (10–20s) giữa các lần mở profile.
  - Khi dính chuỗi lỗi liên tiếp > 3 tài khoản: DỪNG NGAY, để dải proxy nghỉ (cooldown) tối thiểu 30–60 phút hoặc đổi IP proxy trước khi chạy tiếp.

---

## 4. Quản Lý Tiến Trình GPM Chống Treo Taskbar
- **Triệu chứng**: Gọi `GET /api/v3/profiles/stop/{id}` nhưng GPM Browser vẫn để lại hàng chục tiến trình `chrome.exe` mồ côi làm tràn taskbar và đơ máy.
- **Xử lý triệt để**:
  - Lưu lại `profile_path` khi khởi động profile.
  - Sau khi `stop` qua API, quét `psutil` diệt chính xác các tiến trình `chrome.exe` chứa `profile_path` đó trong command line, **tuyệt đối không dùng `taskkill /F /IM chrome.exe` bừa bãi** để tránh tắt nhầm các ứng dụng khác hoặc phone farm `xiaowei`.
