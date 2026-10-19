# Pro Pool Isolation & Pure Login Nurture Decoupling (2026-10-19)

## 1. Bối cảnh & Mục tiêu
- **Phân tách hai nhóm tài khoản trong hệ sinh thái Taadaa**:
  - **Nhóm 1 - Google AI Pro Pool (`g1-pro-tier`)**: Gồm ~21 tài khoản Google AI Pro active được gán vào `ag-gemini-pool-3` phục vụ LLM inference cho Hermes & OmniRoute. Yêu cầu token health check và auto-healer khi hết hạn token.
  - **Nhóm 2 - Tài khoản Farm / Free**: Hàng trăm tài khoản Gmail trên máy Samsung S7 & GPM phục vụ nuôi acc TikTok. Nhóm này **tuyệt đối không được cấp quyền OAuth Antigravity hay nạp lên OmniRoute**. Chỉ thực hiện login sạch lưu session cookie, sau đó chuyển sang Group 10 để cron nuôi tự nhiên (xem YouTube, Google News, Search).

## 2. Quy tắc kiến trúc & Implementation

### A. Tách luồng Login thuần túy (`run_oauth_s7_pipeline.py --login-only`)
- Khi kích hoạt cờ `--login-only`:
  1. Trình duyệt mở thẳng `https://accounts.google.com/ServiceLogin?hl=vi`.
  2. Tự động điền email, mật khẩu, giải reCAPTCHA, và lấy mã OTP/TOTP 2FA (từ Excel hoặc S7 Security Code).
  3. Xác nhận đăng nhập thành công khi URL điều hướng vào `myaccount.google.com` HOẶC phát hiện element avatar Google Account đang hiển thị (`loc.count() > 0 and loc.is_visible()`).
  4. Bỏ qua 100% bước lấy `authUrl` từ `OMNI_BASE/api/oauth/antigravity/authorize` và bỏ qua bước trao đổi `api/oauth/antigravity/exchange`.
  5. Phát sinh telemetry metric:
     - `login_only_success`: kèm mid, email, landing URL.
     - `login_only_failed`: kèm mid, email, reason (timeout/checkpoint).

### B. Giới hạn Healer Watchdog chỉ kiểm tra Pool Pro (`cron_chatgpt_web_pool_watchdog.py`)
- Hàm lọc điều kiện Pro:
  ```python
  def is_pro_antigravity(c: dict) -> bool:
      excluded = {'thanhdatbui19951@gmail.com', 'jinrakal@gmail.com'}
      if (c.get('name') or '').lower() in excluded:
          return False
      psd = c.get('providerSpecificData')
      if psd is not None and isinstance(psd, dict) and 'tier' in psd:
          return psd.get('tier') == 'g1-pro-tier'
      return True
  ```
- **Phạm vi kiểm tra token**:
  - `ag_pro_conns = [c for c in ag_conns if is_pro_antigravity(c) and c.get('isActive')]`
  - `ag_broken = [c for c in ag_pro_conns if c.get('testStatus') != 'active']`
  - **Toàn bộ 100+ tài khoản Free / Standard / Farm bị bỏ qua hoàn toàn**, không bị watchdog mở profile GPM ép nạp OAuth Antigravity.
  - Báo cáo telemetry phản ánh đúng số lượng Pro active (`ag_active_cnt / len(ag_after)`).

### C. Dọn dẹp Combo OmniRoute (`ag-gemini-pool-3`)
- Khi loại trừ tài khoản cá nhân khỏi pool, phải đồng bộ loại bỏ cả trong `provider_connections` và trong mảng `models` của combo `ag-gemini-pool-3` qua `PUT /api/combos/<id>` để tránh lỗi connection stub rỗng hoặc expired models làm loãng round-robin.
