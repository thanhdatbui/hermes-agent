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
  - Kiểm tra xác thực 2 lớp chống false-positive:
    - URL chuyển hướng vào `myaccount.google.com`.
    - HOẶC selector avatar Google Account xuất hiện và đang hiển thị (`loc.count() > 0 and loc.is_visible()`). Lưu ý: bắt buộc dùng `.first` và kiểm tra `is_visible() == True` để tránh lọt phần tử ẩn hoặc stale DOM.
  - **Bỏ qua 100% bước gọi OmniRoute:** Không gọi `api/oauth/antigravity/authorize`, không lấy `authUrl` và không gửi mã `exchange`.
  - Bắn structured telemetry metric: `login_only_success` khi thành công, `login_only_failed` với `reason="timeout"` khi thất bại.
  - Gán profile vào `GroupId = 10` để watchdog nuôi tự nhiên (`cron_gpm_gmail_nurture.py`) nhận diện và chăm sóc.

### B. Giới hạn Phạm vi Quét Token trong Watchdog (Fail-Closed Isolation)
- File: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_chatgpt_web_pool_watchdog.py`
- Bổ sung hàm filter an toàn theo chuẩn **Fail-Closed**:
  ```python
  def is_pro_antigravity(c: dict) -> bool:
      """Chỉ chấp nhận tài khoản Antigravity thuộc Pool Pro (g1-pro-tier), bỏ qua tài khoản Free/Farm.
      Áp dụng chính sách Fail-Closed an toàn: thiếu metadata hoặc tier không rõ ràng -> lập tức loại bỏ."""
      if not isinstance(c, dict):
          return False
      email = str(c.get('name') or c.get('email') or '').strip().lower()
      if not email:
          return False
      excluded = {'thanhdatbui19951@gmail.com', 'jinrakal@gmail.com'}
      if email in excluded:
          return False
      psd = c.get('providerSpecificData')
      if isinstance(psd, dict):
          return psd.get('tier') == 'g1-pro-tier'
      return False
  ```
- **Phạm vi kiểm tra:**
  ```python
  ag_pro_conns = [c for c in ag_conns if is_pro_antigravity(c) and c.get('isActive')]
  ag_broken = [c for c in ag_pro_conns if c.get('testStatus') != 'active']
  ```
- **Hệ quả bảo vệ**:
  - Chỉ kiểm tra token và chỉ kích hoạt luồng OAuth hồi sinh cho 21 tài khoản Pro active.
  - 100+ tài khoản Free/Farm bị bỏ qua hoàn toàn, không bị watchdog mở profile GPM làm gián đoạn tiến trình nuôi acc.
  - Báo cáo tổng kết hiển thị đúng số lượng tài khoản Pro: `• Antigravity (Pro): {ag_active_cnt}/{len(ag_after)} ACTIVE`.
  - Tôn trọng cờ `isActive == True`: tài khoản do user hoặc hệ thống chủ động đưa vào Standby sẽ không bị tự ý bật lại.

### C. Dọn dẹp Danh mục Models Combo (`ag-gemini-pool-3`)
- Khi loại bỏ tài khoản cá nhân hoặc tài khoản hết hạn khỏi pool Pro:
  - Bắt buộc cập nhật danh sách `models` của combo qua REST API: `PUT http://127.0.0.1:20129/api/combos/<id>`.
  - Loại bỏ các model trỏ vào connection rác / connectionId null / tài khoản trong danh sách loại trừ (`thanhdatbui19951@gmail.com`, `jinrakal@gmail.com`), duy trì danh sách sạch chính xác 21 accounts Pro.

## 3. Tiêu Chuẩn Thẩm Định Closeout Gate (Sol High Auditor)
Khi thực hiện thay đổi trên các module lọc tài khoản hoặc watchdog:
1. **Kiểm thử Schema Contract thực tế**: Unit test bắt buộc có test case đối chiếu trực tiếp với fixture schema thực tế của OmniRoute (`g1-pro-tier`, `plan: Pro`, `subscriptionTier: Google AI Pro`).
2. **Negative Tests cho Failure Branches**:
   - Test trường hợp avatar locator tồn tại nhưng ẩn (`is_visible() == False`).
   - Test trường hợp timeout phát sinh `login_only_failed` telemetry.
   - Test trường hợp metadata rỗng, sai kiểu (`str` thay vì `dict`), tier null -> chứng minh hàm lọc trả về `False` (Fail-Closed).
3. **Telemetry Assertion**: Test suite phải assert trực tiếp vào payload của `save_telemetry_metrics` (kiểm tra `recovered_ag`, `failures`, `total_failures`, `antigravity.total`).
