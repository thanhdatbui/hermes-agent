# Hotmail magic-link signup blocker — `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK`

Nguồn: live run STT 30 / serial `ce0217126cd4bc640c` / email `krystalsophroniaadonis7@hotmail.com` (2026-08-11 15:01–15:05).

## Triệu chứng

```
[7c] Lấy OTP TikTok từ inbox: <email>
[7c] TikTok magic-link markers detected -> Gmail semantic-link mode
[otp-gmail] Non-Gmail target -> skip Gmail app and use provider browser
[otp-browser] Mở Outlook web cho <email>
[otp-cdp] Fresh Outlook code found in background tab: [REDACTED]
[otp-enter] Quay lại TikTok, nhập OTP: [REDACTED]
[otp-enter] Cảnh báo: không còn ở màn OTP
✗ STOPPED: [otp-enter] TikTok OTP screen unavailable after Recents recovery
```

Exit code 1. Không có `tracking_result_*.json`, không có write tracking workbook.

## Chẩn đoán (phân biệt với uiautomator treo)

- Dump UI lúc warn (`warn_otp_screen_gone_*.xml`) KHÔNG rỗng (~30KB) → **không phải** uiautomator treo (treo = dump rỗng/`No such file or directory`).
- Text trong cả dump lúc bắt đầu step 7c (`debug_<stt>_otp_screen_*.xml`) và dump warn đều là màn magic-link:
  - `Bạn có thể đăng nhập bằng liên kết được gửi đến <email>`
  - `Kiểm tra hộp thư của bạn`
  - `Gửi lại email` / `Gửi lại email sau N giây` (đếm ngược)
- Không có resource-id field nhập mã OTP → nhánh `[otp-enter]` không có chỗ nhập.
- `dumpsys window` sau khi STOPPED: vẫn `SignUpOrLoginActivity` foreground, VPN Connected — máy khỏe, UI giữ nguyên màn failure (đúng final bookkeeping).

## Root cause

TikTok chọn flow **magic-link** cho email hotmail mới (thay vì OTP số). Script detect magic-link markers nhưng nhánh semantic-link chỉ handle Gmail app; hotmail bị skip → fallback CDP đọc mã trong Outlook (mã có thể xuất hiện trong mail) rồi quay lại TikTok — nhưng TikTok không có field nhập mã nên STOPPED. Đây là **gap handler**, không phải lỗi thứ tự OTP (khác `OTP_REJECTED_AFTER_FRESH_RETRY`).

## Hướng recovery hợp lệ (chưa có handler, không blind retry)

- Click magic-link trong Outlook qua CDP (tương tự semantic-link mode của Gmail) — cần implement handler cho hotmail.
- Hoặc resume tay: chờ mail, mở link trên máy, hoàn tất signup.
- Lock giữ nguyên `handoff` (owner pid đã chết) — takeover sau khi xác minh pid chết.

## Evidence paths (bản ghi gốc)

- Console log: `D:\Taadaa\Tiktok_Reg\artifacts\runs\reg30_rerun\stdout_console.log`
- UI dump warn: `C:\Users\Kibe\AppData\Local\Taadaa\Tiktok_Reg\artifacts\ui_dumps\warn_otp_screen_gone_bcc430cdf8_18132_150458_672638.xml`
- UI dump step 7c: `...\ui_dumps\debug_30_otp_screen_bcc430cdf8_18132_150340_313858.xml`
- Screenshot: `...\screenshots_social\otp_screen_30_bcc430cdf8_18132_150340_318579.png`
- CDP login proof: `...\runs\hotmail-inbox-krystalsophroniaadonis7_hotmail.com\login_20260811_150423.json`
- Tracking row (không đổi sau run): `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx` → Máy=30, ID cũ `ninhvan04061999`, NGÀY TẠO 1999-06-04.
