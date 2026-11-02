---
name: tiktok-farm-hermes-cron-migration
description: >-
  **DEPRECATED (2026-09-10):** Picker/cohort/manifest system da bi user yeu cau bo.
  Runner don gian: tiktok_runner.py doc gio → goi run-feed-session.ps1 tu taikhoan_run_safe.xlsx.
  Xem tiktok-feed-session skill hoac references/cron-schedule-simplified-2026-09-10.md.
  Skill nay giu lam lich su tham khao, KHONG dung cho cong viec moi.
  Migrate TikTok farm scheduling tu Windows Task Scheduler sang Hermes cron orchestration.
---
# TikTok Farm → Hermes Cron Migration

## Mục tiêu
Bỏ Windows Task Scheduler (TikTokScheduler/TikTokAllSchedulerTray/wake tasks), chuyển sang Hermes cron: mỗi account lướt feed (nuôi acc) ngẫu nhiên giờ riêng, lướt xong đăng luôn nếu đến hạn — hết đồng loạt. Picker/runner = script thuần no_agent (0 token LLM); watcher hybrid; chỉ Telegram khi fail hết 2 attempts / blocker thật.

## User chốt (2026-08-10 — cao hơn mọi đề xuất cũ trong plan)
- Mỗi consumer giữ workbook RIÊNG, không hợp nhất: feed/lướt = `taikhoan_run_safe.xlsx` (D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\), upload = `Tik1.xlsx` (có Folder Video/Video Đã Đăng). Picker đọc 2 nguồn qua source-config.json + account_id mapping ổn định.
- Farm 60-74 máy SM-G930F; mỗi máy tối đa 6 acc (target đủ 6).
- Mỗi acc: 2 ngày lướt 1 lần; jitter chỉ TRỄ không sớm (≥3 ngày = hard overdue, ưu tiên cao).
- Mỗi máy/ngày: max 3 acc; 2 acc cùng máy cách ≥ 180 phút.
- Window: 06:00 → 01:00 đêm hôm sau; reserved blocks 12-14 & 17-19 GIỮ NGUYÊN.
- Slot 15 phút; phiên (session_duration) 60 phút.
- Lướt xong đăng luôn trong 1 phiên: action `feed_then_post` (không tách lịch; `post_only` cấm trong picker).
- Lock: consumer là owner duy nhất; runner chỉ preflight → `SKIPPED_DEVICE_LOCKED`, không claim outer lock.
- Recovery: giữ runtime hiện có (chưa từng tự recovery thành công — user cứu tay; fix sau). Attempt 1 → recovery không Telegram; attempt 2 fail → Telegram; blocker thật → Telegram ngay.
- Telegram về Home channel; timezone Asia/Ho_Chi_Minh; runner 15', grace 90' sau slot_time, quá hạn → missed + watcher review.
- Máy chạy 24/7 (không lo wake).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
