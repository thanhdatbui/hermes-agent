---
name: tiktok-add-2fa-batch-ops
description: "Use when running batch 2FA on TikTok farm. Chạy batch 2FA repo tiktok-add-bao-mat-f2a, preflight, rotate pass, verify sau chạy."
---
# TikTok Add 2FA Batch Ops (repo tiktok-add-bao-mat-f2a)

References:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
- `scripts/flush_dpapi_journal_to_workbook.py` — **[MỚI 21/09/2026]** Script tự động flush các Secret Key 2FA từ DPAPI journal vào Cột E file Excel `taikhoan_dat_v2_updated .xlsx`, đối chiếu readback và cập nhật state WRITTEN.
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

## Đổi Email liên kết TikTok sang Hotmail mới (Bỏ qua OTP mail cũ & chống dính recovery)
- **Bản chất phát hiện TikTok UI (18/09/2026):** Tài khoản TikTok no-phone đã bật 2FA TOTP và đăng nhập lâu ngày trên thiết bị: khi vào `Hồ sơ -> Cài đặt và quyền riêng tư -> Tài khoản -> Thông tin tài khoản -> Email -> Thay đổi email`, TikTok **MỞ THẲNG MÀN HÌNH "NHẬP EMAIL MỚI"** mà **hoàn toàn KHÔNG bắt OTP từ mail cũ**.
- **Quy trình đổi email tự động:**
  1. Mua Hotmail mới qua API shop: `python D:/Taadaa/tools/buy_hotmail.py --buy 1 --target-file <path>` lấy `email|pass|refresh_token|client_id`.
  2. Vào TikTok `Thay đổi email` -> Gõ Hotmail mới -> Bấm "Tiếp tục".
  3. Polling mã OTP 6 số từ Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages`) qua `refresh_token` & `client_id`.
  4. Nhập 6 số OTP vào TikTok để hoàn tất liên kết email mới.
  5. Cập nhật Hotmail mới vào Cột F và Pass Hotmail vào Cột G file Excel `taikhoan_dat_v2_updated .xlsx`.
- **Quy tắc bảo mật bàn giao:** Hotmail bán kèm nick CẤM add email khôi phục cá nhân. Luồng chuẩn: Đổi pass Chrome -> Bấm Sign out everywhere -> Lưu Cột G Excel -> Đăng nhập App Outlook bằng pass mới.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
