# Quy Trình Xử Lý TikTok Silent Drop Mail OTP & Khắc Phục Lỗi Máy Admin Trong tiktok_login_v1

> **Date:** 2026-10-09  
> **Trigger:** Farm Alert `[PREFLIGHT REG BÙ ROW N]`:
> 1. Lỗi OTP `[7c]` lặp lại do TikTok Silent Drop trên một địa chỉ Hotmail cụ thể.
> 2. Lỗi `[03_dropdown]` kẹt Switcher do tài khoản bị văng phiên (session expired) về One-tap login.
> 3. Lỗi `tiktok_login_v1.py` crash `Khong co STT N trong ACCOUNTS` trên cụm Admin (N >= 201).

---

## 1. Dấu Hiệu TikTok "Silent Drop" Mailbox OTP & Cách Xử Lý Dứt Điểm

### Hiện tượng & Bản chất:
- Trên app TikTok, màn hình vẫn hiển thị countdown: *"Sử dụng liên kết này hoặc mã được gửi đến <email> (58s)"*.
- Nhưng qua Microsoft Graph API (OAuth2 `refresh_token` + `client_id` kết nối HTTP 200), hòm thư Inbox / Junk Email hoàn toàn **0 có bất kỳ email nào từ noreply@tiktok.com**.
- **Nguyên nhân**: Risk engine phía backend của TikTok đánh giá mail mới tạo / low-trust hoặc đã bị flag từ các đợt reg trước và âm thầm chặn dispatch gửi mã (Silent Drop).
- Nếu không cách ly, ở các đợt reg bù tiếp theo (Row 6, Row 7...), bộ chọn target sẽ bốc lại đúng email kẹt này, gây lặp lại lỗi timeout `[7c]`.

### Quy trình đổi mail chuẩn hóa O(1):
1. **Cách ly email lỗi**:
   - Cập nhật cột `trạng thái` (cột 11) của email trong `admin/gmail_clean_v2.xlsx` thành `skip_otp_timeout` (luôn tạo bản sao `.bak_<timestamp>` trước khi lưu).
   - Thêm email vào file `D:/Taadaa/Tiktok_Reg/data/registered_emails_blacklist.json` để detector `_detect_clean.py` và `ensure_row_accounts.py` vĩnh viễn bỏ qua email này.
2. **Chuyển sang mail aged / high-trust**:
   - Kiểm tra các email kế tiếp của máy đó trong `gmail_clean_v2.xlsx`.
   - Dùng script Graph API kiểm tra nhanh: token OAuth2 LIVE (HTTP 200) và hòm thư đã có sẵn thư lịch sử (aged mail).
3. **Kích hoạt lại reg bù**:
   - Chạy lệnh reg bù đích danh máy:
     `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/<cluster>.yaml" python -u D:/Taadaa/tools/ensure_row_accounts.py <row> --machines <stt>`

---

## 2. Xử Lý Máy Bị Văng Phiên (Session Expired) Gây Kẹt Account Switcher

### Hiện tượng:
- Máy chỉ có 1 hoặc 2 tài khoản, khi vào Profile bấm vào tên tài khoản hoặc chevron ▼ thì **Account Switcher không bung ra**.
- Fallback vào *Cài đặt và quyền riêng tư* thì dưới đáy chỉ có nút *"Đăng xuất"*, không có *"Chuyển đổi tài khoản"*.

### Bản chất:
- Toàn bộ tài khoản trên app đã bị văng phiên (session expired/logged out) và bị đẩy ra màn hình lưu trữ One-tap Login (*"Chào mừng bạn trở lại"*).
- App không có phiên active nào nên không thể tải context Account Switcher.

### Giải pháp:
- **KHÔNG cố bấm tay ADB** hay swipe mù.
- Chạy script login tự động để kích hoạt lại phiên cho các tài khoản cũ trước:
  `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/<cluster>.yaml" python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <stt> --email <username> --ss`
- Khi tài khoản cũ active lại, Account Switcher sẽ hoạt động bình thường và mở lại luồng reg/thêm nick mới.

---

## 3. Bản Vá Multi-Cluster Awareness Trong `tiktok_login_v1.py`

### Lỗi:
- Trước đây hàm `resolve_device(stt)` trong `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py` chỉ tra cứu danh sách tĩnh `ACCOUNTS` (chỉ chứa STT 1–80 của cụm Kibe).
- Khi gọi cho cụm Admin ($STT \ge 201$), script văng lỗi `RuntimeError: Khong co STT <stt> trong ACCOUNTS`.

### Chuẩn hóa O(1):
```python
def resolve_device(stt):
    acc = next((item for item in ACCOUNTS if item["stt"] == stt), None)
    if acc and acc.get("device"):
        return acc["device"]
    from project_paths import TARGET_INVENTORY_WORKBOOK
    from scripts.target_inventory import load_machine_devices
    dev = load_machine_devices(TARGET_INVENTORY_WORKBOOK).get(stt)
    if dev:
        return dev
    raise RuntimeError(f"Khong co STT {stt} trong ACCOUNTS")
```
- Tự động nhận diện file `TARGET_INVENTORY_WORKBOOK` theo host (`taikhoan_run_safe.xlsx`) để trỏ chuẩn serial cho toàn bộ 160 máy cả 2 cụm Kibe và Admin.
- Bộ test hồi quy xác minh: `PYTHONPATH="D:/Taadaa/Tiktok_Reg" pytest D:/Taadaa/Tiktok_Reg/tests/test_tiktok_login_v1.py` PASS 100%.
