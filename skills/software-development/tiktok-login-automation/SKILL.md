---
name: tiktok-login-automation
description: "TikTok login automation via ADB — inventory, login, 2FA, UI handling for both legacy (46.x) and new UI."
---
# TikTok Login Automation

## 1. Nguyên Tắc Cốt Lõi
- **Tài sản doanh nghiệp (FARM-ASSET-001):** Cấm tự ý logout tài khoản trên máy farm trừ trường hợp xác nhận là nick ký sinh qua `do_logout_account.py`.
- **Pass ảo / Passwordless:** Khi cột Mật khẩu trong Excel rỗng, đăng nhập qua OTP email hoặc 2FA TOTP (`--otp-only`).
- **Bắt Buộc Dùng Canonical Account Switcher Trong automation-core (FARM-SWITCHER-001):** CẤM TUYỆT ĐỐI tự viết ad-hoc switcher bằng OCR hoặc tap tọa độ mù. Mọi script/runner chuyển acc trên farm BẮT BUỘC dùng `automation_core.tiktok.account_switcher` (qua `FollowAdapter`). Chi tiết xem tại [`references/canonical-account-switcher-automation-core-mandate.md`](references/canonical-account-switcher-automation-core-mandate.md).
- **Bảo Vệ Switcher Pre-Opened & Tọa Độ Edit Profile S7 (2026-10-20):**
  * Khi gọi switcher, bắt buộc kiểm tra `is_switcher_open(adapter)` trước khi gọi `open_account_switcher` để tránh lỗi `PROFILE_TARGET_NOT_FOUND` do khay switcher che khuất bottom nav.
  * Nếu chuyển switcher thất bại trong trạng thái `SWITCHER`, không `raise Abort` ngay mà thực hiện `keyevent 4` để đóng khay.
  * Tọa độ fallback nút Sửa hồ sơ trên Galaxy S7 là `(870, 558)`, cấm tap vào vùng `y >= 680` (vùng nút Bio). Chi tiết xem [`references/switcher-pre-opened-state-and-edit-profile-bounds-20261020.md`](references/switcher-pre-opened-state-and-edit-profile-bounds-20261020.md).
- **Tra cứu O(1):** Dùng `python D:/Taadaa/tools/inspect_machine.py <N>`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
