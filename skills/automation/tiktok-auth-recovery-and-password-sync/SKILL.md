---
name: tiktok-auth-recovery-and-password-sync
description: Use when TikTok login has wrong pass. Reset via token.
---
# TikTok Auth Recovery & Password Sync

> Reference Case Studies: `references/case-study-m211-recovery.md` (M211 wrong password recovery via Graph API OTP & single-writer lock), `references/case-study-m261-fake-password-and-canary-row-trap.md` (M261 data governance on fake password vs empty/None, remote Admin socket & anti-performative canary row selection), `references/case-study-m274-switcher-digit-collision-and-winrt-ocr-enforcement.md` (M274 switcher digit suffix collision bug fix, WinRT OCR primary enforcement to protect S7 CPU, and GPM profile OTP fallback), `references/case-study-login-v1-cluster-awareness-and-playwright-path-pollution.md` (tiktok_login_v1.py cluster awareness for Admin machines >= 200, sys.path sanitization for Playwright against broken hermes-agent venv greenlet, and account dropdown already open handling), `references/smvmail-recovery-auto-bypass-script.md` (Tự động giải Microsoft Security Challenge qua API smvmail.com bằng script thay vì báo kẹt hay ghi nhớ suông), `references/tiktok-otp-throttling-and-replacement-triage.md` (Phát hiện TikTok OTP throttling và quy trình thay thế tài khoản dự phòng chống nghẽn ca nuôi), `references/case-study-outlook-focused-vs-other-tab-otp-trap.md` (Bẫy phân loại 2 tab Ưu tiên vs Khác trên Outlook Web nuốt mã OTP TikTok và cơ chế auto switch tab).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
