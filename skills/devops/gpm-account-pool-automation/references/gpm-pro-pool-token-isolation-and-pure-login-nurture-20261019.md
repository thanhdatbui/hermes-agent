# GPM Pro Pool Token Isolation & Pure Login Nurture Protocol (2026-10-19)

## 1. Bối cảnh Vận hành & Phân định Ranh giới
- Trong hệ thống Taadaa, tài khoản Google được chia làm 2 phân vùng với mục đích sử dụng hoàn toàn khác nhau:
  1. **Pool Pro (`g1-pro-tier`)**: Dàn ~21 tài khoản Google AI Pro (`plan: Pro`, `ag-gemini-pool-3`), dùng để cung cấp quota API cao cấp cho hệ thống điều phối Coordinator / Worker. Dàn này yêu cầu kiểm tra token liveness định kỳ và tự động refresh qua GPM khi hết hạn.
  2. **Dàn Nick Nuôi Farm (Free / Standard)**: Hàng trăm tài khoản Gmail trên điện thoại Samsung S7 và GPMLogin phục vụ nuôi nick TikTok. Dàn này **CẤM TUYỆT ĐỐI** liên kết OAuth Antigravity hay đăng ký lên OmniRoute.

## 2. Quy chuẩn Kỹ thuật Triển khai

### A. Tách Luồng Đăng nhập Thuần (`--login-only`)
- File: `D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py`
- Khi truyền tham số `--login-only`:
  - Mở trực tiếp trang đăng nhập chuẩn: `https://accounts.google.com/ServiceLogin?hl=vi`.
  - Tự động điền email, mật khẩu, giải reCAPTCHA và điền mã TOTP 2FA / S7 Security Code.
  - Kiểm tra xác thực 2 lớp:
    - URL chuyển hướng vào `myaccount.google.com`.
    - HOẶC selector avatar Google Account xuất hiện và đang hiển thị (`loc.count() > 0 and loc.is_visible()`).
  - **Bỏ qua 100% bước gọi OmniRoute:** Không gọi `api/oauth/antigravity/authorize`, không lấy `authUrl` và không gửi mã `exchange`.
  - Bắn structured telemetry metric: `login_only_success` khi thành công, `login_only_failed` khi timeout.

### B. Giới hạn Phạm vi Quét Token trong Watchdog
- File: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_chatgpt_web_pool_watchdog.py`
- Bổ sung hàm filter an toàn:
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
- **Phạm vi kiểm tra:**
  ```python
  ag_pro_conns = [c for c in ag_conns if is_pro_antigravity(c) and c.get('isActive')]
  ag_broken = [c for c in ag_pro_conns if c.get('testStatus') != 'active']
  ```
- **Hệ quả bảo vệ**:
  - Chỉ kiểm tra token và chỉ kích hoạt luồng OAuth hồi sinh cho 21 tài khoản Pro active.
  - 100+ tài khoản Free/Farm bị bỏ qua hoàn toàn, không bị watchdog mở profile GPM làm gián đoạn tiến trình nuôi acc.
  - Báo cáo tổng kết hiển thị đúng số lượng tài khoản Pro: `• Antigravity: {ag_active_cnt}/{len(ag_after)} ACTIVE`.

### C. Dọn dẹp Danh mục Models Combo (`ag-gemini-pool-3`)
- Khi loại bỏ tài khoản cá nhân hoặc tài khoản hết hạn khỏi pool Pro:
  - Bắt buộc cập nhật danh sách `models` của combo qua REST API: `PUT http://127.0.0.1:20129/api/combos/<id>`.
  - Loại bỏ các model trỏ vào connection rác / connectionId null / tài khoản trong danh sách loại trừ (`thanhdatbui19951@gmail.com`, `jinrakal@gmail.com`), duy trì danh sách sạch chính xác 21 accounts Pro.
