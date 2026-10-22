---
name: cron-reboot-window-safety
description: "Use when an all-day cron must avoid fixed reboot windows."
---

# Cron Reboot-Window Safety

Use this skill when a watchdog or batch is intentionally scheduled throughout the day but a host-level reboot/reset runs at fixed times. The correct solution is an in-process blackout guard, not silently narrowing the cron schedule or pausing the job.

## Workflow

1. **Establish live facts first.** Read the cron entry, confirm its schedule, inspect the reboot/preflight log, and identify the actual lock-holder process and parent command line. Do not infer the culprit from the job name.
2. **Preserve the business schedule.** If the requirement is “run all day, avoid reboot,” leave the cron expression unchanged (for example, `*/15 * * * *`).
3. **Patch the existing predicate.** Add reboot blackout checks to the watchdog’s existing safe-window function. Preserve current feed, cache, device-lock, and idempotency guards.
4. **Use explicit bounded windows.** For fixed reboot times, define a documented pre/post buffer. The validated Taadaa pattern is 15 minutes before and after 05:20, 11:20, and 17:20: `05:05–05:34`, `11:05–11:34`, `17:05–17:34`.
5. **Test boundaries, not just the center.** Cover the first and last blocked minute of each window and at least one minute immediately outside a window. Run the focused test file and retain the real output.
6. **Deploy consistently.** After verification, sync the source artifact to the Hermes runtime copy and shared cron deployment according to repository deployment discipline. Verify the cron expression was not changed.
7. **Validate incidents from evidence.** If a reboot is skipped, inspect the reboot log, system boot time, active device locks, and process creation/parentage. A skipped reboot is not evidence that the scheduler failed; it may be a deliberate lock-safety result.

## Patch contract

For a small targeted fix, constrain the edit to the existing safe-window function and focused tests. Do not introduce a new scheduler, dependency, broad refactor, or device-side workaround. Keep the diff small and run one focused offline test command where possible.

## Safety rules

- Never pause or remove the all-day cron when the requested behavior is only reboot avoidance.
- Never move a daytime watchdog to a night-only schedule without an explicit business decision.
- Never use device taps, force-stops, or lock deletion to work around a scheduler collision.
- Do not report deployment as complete until source, runtime copy, focused test result, and schedule are all verified.
- Daily host reboot preflight (`farm_preflight_daily_reset.py`) must preserve in-flight Telegram sessions with `lookback_minutes >= 60` (not 20m) and include sessions with recent `tool` activity even if `last_role == 'assistant'`, preventing post-reboot session drop and multi-hour coordinator stalls.
- Never report test suite counts (e.g. 131 passed) or declare a fix complete before the command has actually exited 0 with inspectable stdout. Background tests that time out in foreground must be waited/polled to real completion before any status claim.
- Bẫy Safe Window không đệm làm trôi ca Reboot: Các cron xen ca (như `tiktok_rename_rolling_watchdog.py`) có Safe Window kết thúc sát giờ reboot (`hm < 680` cho 11:20, `hm < 1040` cho 17:20) sẽ nhận batch lúc 11:15 hoặc 17:15 và giữ active device lock đúng lúc Task Scheduler kích hoạt one-shot trigger, làm hủy reboot cả ca. Safe Window của cron xen ca BẮT BUỘC đóng trước mốc reboot tối thiểu 20 phút (11:00, 17:00), và Task Scheduler/preflight script cần có cơ chế retry 5 phút trong khung 20 phút (11:20-11:40, 17:20-17:40) chờ lock nhả thay vì skip bỏ luôn cả ca.
- Bẫy Claim Lane Deadlock ca đêm (Night Chain): Khi watchdog chạy batch dài (ví dụ: `cron_night_tiktok_2fa_watchdog.py` chạy Reg Gmail nối tiếp Add 2FA TikTok), nếu xuất phát sát giờ ca sáng (05:05) hoặc giờ reboot (05:20), tiến trình sẽ bị SIGKILL giữa chừng trong khi đang giữ cờ `running_since`. Cờ này có TTL tới 5400s (90 phút) làm kẹt toàn bộ các lần trigger kế tiếp. BẮT BUỘC: (1) Kiểm tra thời gian còn lại trước ca sáng/reboot >= 45 phút mới cho phép claim lane; (2) Có cơ chế tự dọn cờ claim mồ côi nếu không có tiến trình con nào đang thực sự chạy.
- Bẫy Cron Watchdog đa Phase gửi dồn về Farm Alerts (Multi-Phase Watchdog Routing): Khi một watchdog chạy chuỗi gồm nhiều Phase thuộc các repo khác nhau (ví dụ: Phase 1 Reg Gmail -> Phase 2 Add 2FA TikTok trong `post_noon_chain_watchdog` hoặc `cron_night_tiktok_2fa_watchdog`):
  + CẤM: Đặt cron `deliver: telegram:<chat_id>` trong `jobs.json` rồi print báo cáo ra stdout; Hermes cron sẽ gom toàn bộ output gửi về một nhóm duy nhất (thường là Farm Alerts `-5373649734`), gây loạn thông báo và phá vỡ quy hoạch nhóm theo repo.
  + CHUẨN: Đặt cron `deliver: local` trong `jobs.json`. Trong watchdog script, tự dispatch report từng phase về đúng chat ID tương ứng (`GMAIL_REPORT_CHAT_ID = "-5139245637"`, `TIKTOK_REPORT_CHAT_ID = "-5468653590"`) qua `dispatch_report()` / `_send_telegram_text()`. Báo cáo từng phase phải độc lập và có header phân biệt rõ ràng.

## References

- `references/reboot-blackout-guard-and-all-day-cron.md` — validated window math, evidence checklist, and common collision pitfalls.
- `references/reboot-session-preservation-and-anti-silent-drop.md` — 60m lookback window, assistant-last tool activity detection, and anti-confabulation testing rules.
