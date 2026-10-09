# GPM Hotmail Lifecycle & Change Info Pitfalls (Farm Automation)

## 1. Môi trường Thực thi & Kênh Báo Cáo (User Invariant 2026-10-06)
- **Môi trường thực thi**: Toàn bộ chu trình Hotmail nuôi và bảo mật trên farm (Login -> ChatGPT Reg -> Codex OAuth -> Ngâm 7 ngày -> Change Info) được **tích hợp chạy tự động trên GPMLogin Browser CDP**, **TUYỆT ĐỐI KHÔNG chạy trên điện thoại S7**.
  - Script điều phối: `D:\Taadaa\GPM auto\scripts\batch_gpm_5profiles_supervisor.py`
  - Script đổi mật khẩu & sign out: `D:\Taadaa\Hotmail\scripts\gpm_change_hotmail_security.py`
- **Kênh báo cáo bắt buộc**:
  - Báo cáo định kỳ 6h (`cron_hotmail_gpm_lifecycle_6h_report.py`) **BẮT BUỘC gửi về Farm Alert (`telegram:-5373649734`)**.
  - Tuyệt đối không tự ý chuyển hướng gửi về DM cá nhân của User trừ khi User có yêu cầu riêng.

## 2. Bốn Cạm Bẫy Kẹt Logic Cốt Lõi (Lifecycle Traps)

### Trap 1: Giam lỏng vĩnh viễn ở `WAIT_7D` do thiếu trường đăng nhập
- **Triệu chứng**: Hàng trăm tài khoản đủ tuổi (> 7 ngày) nhưng không bao giờ chuyển sang `CHANGE_INFO`.
- **Nguyên nhân**: Code cũ chỉ kiểm tra `parse_time(info.get("hotmail_login_at")) >= 7 * 86400`. Các tài khoản được cấp thẳng OAuth token sẽ không có `hotmail_login_at` (`None`), khiến biểu thức luôn trả về `False`.
- **Cách xử lý chuẩn**:
  ```python
  anchor_str = (
      info.get("hotmail_login_at")
      or info.get("codex_oauth_at")
      or info.get("chatgpt_registered_at")
  )
  anchor_time = parse_time(anchor_str)
  ready = anchor_time is not None and (datetime.now(timezone.utc) - anchor_time).total_seconds() >= 7 * 86400
  ```

### Trap 2: Slicing `STAGE_ORDER` nuốt stage `CHANGE_INFO` thành `DONE` ảo
- **Triệu chứng**: Supervisor báo thành công `DONE` liên tục nhưng tài khoản chưa từng được đổi pass hay sign out.
- **Nguyên nhân**: `STAGE_ORDER` có dạng:
  `["HOTMAIL_LOGIN", "CHATGPT_REG", "CODEX_OAUTH", "WAIT_7D", "CHANGE_INFO", "REMOVE_RECOVERY", "SIGN_OUT_EVERYWHERE", "RELOGIN_NEW_PASSWORD", "DONE"]`
  Nếu dùng slice `STAGE_ORDER[5:-1]` thì index 4 (`CHANGE_INFO`) bị bỏ qua, rơi thẳng vào fallback `return {"status": "DONE"}`.
- **Cách xử lý chuẩn**: Tách riêng nhánh `if stage == "CHANGE_INFO"`:
  ```python
  if stage == "CHANGE_INFO":
      cmd = [sys.executable, str(CHANGE_INFO_SCRIPT), "--email", info["email"], "--live"]
      if info.get("machine"):
          cmd.extend(["--machine", str(info["machine"])])
      ok = run_cmd(cmd, timeout=1200)
      return {"key": key, "status": "COMPLETED" if ok else "FAILED", "stage": stage, "next_stage": "DONE" if ok else stage}
  ```

### Trap 3: Tìm Profile GPM khi kho vượt quá 100 Profiles
- **Triệu chứng**: Báo không tìm thấy profile GPM cho máy/email mặc dù profile có tồn tại trên GPM.
- **Nguyên nhân**: `client.list_profiles(per_page=100)` mặc định chỉ trả trang đầu tiên. Khi kho có > 600 profiles, các profile ở trang sau bị bỏ sót. Ngoài ra, tìm theo số máy có thể nhầm với profile Gmail cũ.
- **Cách xử lý chuẩn**:
  - Dùng vòng lặp `while True` tăng `page` đến khi hết danh sách.
  - Ưu tiên tìm profile có chứa chuỗi `email` chính xác trong tên profile trước khi fallback theo số máy:
  ```python
  email_lower = email.strip().lower()
  for p in profiles:
      if email_lower in str(p.get("name", "")).lower():
          return p
  ```

### Trap 4: Nút "Sign out everywhere" nằm ngoài viewport và cần confirm popup
- **Triệu chứng**: Đổi pass xong nhưng không kích hoạt được Sign out everywhere để thu hồi token bên bán.
- **Nguyên nhân**: Mục Sign out nằm dưới đáy trang `https://account.live.com/proofs/manage/additional`. Playwright kiểm tra `is_visible` có thể thất bại nếu chưa cuộn trang.
- **Cách xử lý chuẩn**:
  - Cuộn trang trước: `page.evaluate("window.scrollTo(0, document.body.scrollHeight)")`.
  - Dùng `.last.scroll_into_view_if_needed()` với danh sách selector ưu tiên thẻ `<a>` và `<button>`:
    `["a:has-text('Đăng xuất khỏi mọi nơi')", "a:has-text('Sign out everywhere')", "button:has-text('Đăng xuất khỏi mọi nơi')", "#sign-out-everywhere-button"]`.
  - Chờ và click xác nhận nếu xuất hiện modal confirm:
    `page.locator("button:has-text('Đăng xuất'), button:has-text('Sign out'), #btnSignOutEverywhere")`.
