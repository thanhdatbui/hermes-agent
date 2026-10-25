# Proactive Pool Auto-Heal & Turnstile / OAuth Rescue Protocol

## 1. Nguyên Tắc Cốt Lõi: Cứu Acc Thay Vì Cô Lập Bỏ Mặc
- Khi nhận Farm Alert hoặc Watchdog Report về tài khoản pool bị lỗi (`EMPTY_SESSION_TOKEN`, `Timeout OAuth`, `401`), việc database set `is_active = 0` chỉ là bước phòng vệ tạm thời để không gây lỗi 5xx cho router.
- **CẤM TUYỆT ĐỐI** Coordinator dừng lại báo cáo "đã cô lập an toàn" rồi đứng im phân trần. Người dùng coi đây là hành vi phá hoại tài khoản ("sao đéo cứu acc đi mà đi cô lập, mày phá v").
- **Kỷ luật thực thi**: BẮT BUỘC kích hoạt ngay Worker subagent để tự động đăng nhập lại (Re-login / Re-OAuth), lấy session token mới, khôi phục `is_active = 1` và trả về bằng chứng Gate 6 thực tế.

## 2. Cloudflare Turnstile iFrame Bypass Trap (ChatGPT-Web)
- **Hiện tượng**: Khi vào `chatgpt.com/auth/login`, trang xuất hiện thử thách Cloudflare Turnstile ("Verify you are human"). Nếu script chỉ tìm selector ở `page`, checkbox sẽ không bao giờ được click do nằm trong iframe bảo vệ, dẫn tới cạn timeout và báo lỗi ảo `EMPTY_SESSION_TOKEN`.
- **Kỹ thuật xử lý chuẩn**:
  ```python
  def wait_for_turnstile(page, timeout_s=8):
      start = time.time()
      while time.time() - start < timeout_s:
          try:
              for frame in page.frames:
                  if "turnstile" in frame.url or "challenge" in frame.url:
                      cb = frame.locator('input[type="checkbox"], .ctp-checkbox-label, #challenge-stage').first
                      if cb.is_visible(timeout=1000):
                          cb.click()
                          time.sleep(2)
                          return True
          except Exception:
              pass
          time.sleep(0.5)
      return False
  ```
- Duyệt qua `page.frames`, định vị iframe chứa chuỗi `turnstile` hoặc `challenge` và click trực tiếp vào hộp kiểm bên trong frame.

## 3. Codex OAuth Google Redirection & Live TOTP Handling
- **Hiện tượng**: Khi thực hiện Codex OAuth qua endpoint `/api/oauth/codex/start-callback-server`, OpenAI chuyển hướng sang `accounts.google.com/v3/signin/identifier?...`. Nếu script thụ động chỉ chờ nút `Authorize` trên OpenAI, tiến trình sẽ timeout sau 90s.
- **Kỹ thuật xử lý chuẩn**:
  - Đọc credentials từ `gmail_clean_v2.xlsx` (cột 1: email, cột 2: password, cột 3: totp secret, cột 4: recovery email).
  - Điền email vào `#identifierId` -> click Next.
  - Điền password vào `input[type="password"]` -> click Next.
  - Khi Google yêu cầu mã xác minh 2FA / Authenticator: sinh mã TOTP live tức thời bằng `pyotp.TOTP(secret).now()` và điền vào form.
  - Intercept redirect về cổng callback 1455 (`http://localhost:1455/callback?code=...`) và thay `localhost` bằng `127.0.0.1` để gửi code về server.
  - Poll callback từ OmniRoute cho đến khi nhận được `connectionId`.

## 4. Coordinator Guard Contracts cho `delegate_task`
Khi Coordinator phân vai dispatch Worker để thực hiện tác vụ cứu acc hoặc thám nghiệm hiện trường, phải tuân thủ nghiêm ngặt các rào cản cơ giới hóa (Hard Gates):
1. **TASK_KIND**: Bắt buộc ghi rõ `TASK_KIND: INVESTIGATE` (hoặc `TASK_KIND: EDIT`) trong `context`.
2. **TARGET_FILE**: Bắt buộc chỉ định `TARGET_FILE: <đường_dẫn_file>` cụ thể.
3. **FAIL_FAST Clause**: Bắt buộc chứa câu điều kiện fail-fast:
   `FAIL_FAST: Nếu trong <= 3 iterations đầu nhận thấy scope bất khả thi hoặc gặp checkpoint không thể giải quyết thì PHẢI DỪNG NGAY (ABORT) và trả về nguyên nhân + ảnh chụp bằng chứng.`
4. **Budget Cap**: Ngân sách tác vụ điều tra bắt buộc `<= 8 calls` (`Budget điều tra <= 8 calls`). Nếu đặt 15 calls sẽ bị Hard Gate #3 chặn ngay lập tức.
