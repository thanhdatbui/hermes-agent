---
name: tiktok-login-automation
description: "TikTok login automation via ADB — inventory, login, 2FA, UI handling for both legacy (46.x) and new UI."
---

# TikTok Login Automation

## 1. Nguyên Tắc Cốt Lõi
- **Tài sản doanh nghiệp (FARM-ASSET-001):** Cấm tự ý logout tài khoản trên máy farm trừ trường hợp xác nhận là nick ký sinh qua `do_logout_account.py`.
- **Pass ảo / Passwordless:** Khi cột Mật khẩu trong Excel rỗng, đăng nhập qua OTP email hoặc 2FA TOTP (`--otp-only`).
- **Tra cứu O(1):** Dùng `python D:/Taadaa/tools/inspect_machine.py <N>`.

## 2. Quy Trình Vận Hành Đăng Nhập
- **Cài đặt APK:** Sử dụng bộ cài chuẩn qua `install_farm_apks.py`.
- **Đọc OTP Hotmail:** Đọc trực tiếp qua Microsoft Graph API token từ PC, không dùng tay hay app Outlook chậm chạp.
- **2FA TOTP:** Tự động sinh mã xác thực bằng thư viện TOTP chuẩn theo Secret Key lưu trong workbook.

## 3. Tài Liệu Tham Khảo (References)
- Chi tiết các case study đăng nhập và xử lý UI: xem danh mục trong thư mục `references/` của skill.
