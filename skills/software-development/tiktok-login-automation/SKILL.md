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

## 2. Quy Trình Vận Hành Đăng Nhập
- **Cài đặt APK:** Sử dụng bộ cài chuẩn qua `install_farm_apks.py`.
- **Đọc OTP Hotmail:** Đọc trực tiếp qua Microsoft Graph API token từ PC, không dùng tay hay app Outlook chậm chạp.
- **2FA TOTP:** Tự động sinh mã xác thực bằng thư viện TOTP chuẩn theo Secret Key lưu trong workbook.
- **Tự Động Phục Hồi Khi Thiếu Nick (Missing Account Auto-Recovery - 2026-10-17):**
  * Khi các tác vụ Upload hoặc Feed Session báo `ACCOUNT_VERIFY_MISMATCH` hoặc `account-switcher-missing-expected`: CẤM dừng lại than khóc hay hỏi xin phép. BẮT BUỘC kích hoạt ngay canonical runner:
    `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <TARGET_ACCOUNT> --ss`
  * Script tự động mở app, vào Profile, mở Account Switcher; nếu nick đã có trong Switcher thì tự switch phiên, nếu chưa có thì tự động điền form đăng nhập theo credentials trong tracking workbook (hỗ trợ 2FA TOTP bypass OTP mail).
  * **Tự Động Phục Hồi Trong Runner Đổi Tên & Bẫy Kẹt Loop Switcher:** Xem chi tiết tại [`references/tiktok-switcher-active-account-loop-and-login-recovery-20261020.md`](references/tiktok-switcher-active-account-loop-and-login-recovery-20261020.md) (xử lý văng nick, tránh loop tap vào acc đang active trên Profile, và nhận diện cây bút chì layout canh giữa).
  * **Xử lý kẹt ADB Daemon trên máy S7 (ADB Socket Hang Trap):** Nếu lệnh ADB bị timeout ở các lệnh shell cơ bản (`settings put system accelerometer_rotation 0`, `getprop sys.boot_completed`), đó là do ADB daemon socket bị kẹt. BẮT BUỘC chạy `adb kill-server && adb start-server` để thông đường truyền trước khi retry login.
  * **Bẫy Nút Thêm Tài Khoản Kẹt Mép Đáy & Va Chạm Profile vs Home Feed (2026-10-21):** Khi máy đã có 7 nick, nút `Thêm tài khoản` bị dồn xuống đáy `bounds=[0,1788][1080,1920]`. Tapping trực tiếp không scroll sẽ bị nuốt cảm ứng và return mù, dẫn tới `choose_email_login` nhầm màn Profile thành Home feed rồi crash `STOPPED: [06]`. Bắt buộc auto-swipe lên trước khi tap và loại trừ marker profile đã login. Xem chi tiết tại [`references/account-switcher-bottom-cutoff-and-login-profile-feed-collision-20261021.md`](references/account-switcher-bottom-cutoff-and-login-profile-feed-collision-20261021.md).

## 3. Tài Liệu Tham Khảo (References)
- Chi tiết các case study đăng nhập và xử lý UI: xem danh mục trong thư mục `references/` của skill.
