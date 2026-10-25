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
7. **Validate incidents from evidence.** If a reboot is skipped, inspect the reboot log, system boot time, active device locks, and process creation/parentage. A skipped reboot is not evidence that the scheduler failed; it may be a deliberate lock-safety result (`skipped_active_device_lock` or `aborted_in_match`).
   - Fast O(1) audit checklist:
     * System boot time: `python -c "import datetime, psutil; print(datetime.datetime.fromtimestamp(psutil.boot_time()))"`
     * Shift reboot log: Read the tail of `C:\Taadaa_Service\daily_reset.log` for the target shift (`05:20`, `11:20`, or `17:20`).
     * Sentinel flag check: Check existence of `C:\Taadaa_Service\reboot_sentinel_<date>_<shift>_<machine>.flag`.
     * Safe live preflight check: `python D:/Taadaa/tools/services/Taadaa_Service/farm_preflight_daily_reset.py --check-only` to test TFT game detection and Admin PC SSH health without issuing reboot.

## Patch contract

For a small targeted fix, constrain the edit to the existing safe-window function and focused tests. Do not introduce a new scheduler, dependency, broad refactor, or device-side workaround. Keep the diff small and run one focused offline test command where possible.

## Safety rules

- Never pause or remove the all-day cron when the requested behavior is only reboot avoidance.
- Never move a daytime watchdog to a night-only schedule without an explicit business decision.
- Never use device taps, force-stops, or lock deletion to work around a scheduler collision.
- Do not report deployment as complete until source, runtime copy, focused test result, and schedule are all verified.
- Daily host reboot preflight (`farm_preflight_daily_reset.py`) must preserve in-flight Telegram sessions with `lookback_minutes >= 60` (not 20m) and include sessions with recent `tool` activity even if `last_role == 'assistant'`, preventing post-reboot session drop and multi-hour coordinator stalls.
- Never report test suite counts (e.g. 131 passed) or declare a fix complete before the command has actually exited 0 with inspectable stdout. Background tests that time out in foreground must be waited/polled to real completion before any status claim.
- Bẫy Safe Window không đệm làm trôi ca Reboot: Các cron xen ca (như `tiktok_rename_rolling_watchdog.py` hoặc batch 2FA/Gmail) có Safe Window kết thúc sát giờ reboot sẽ nhận batch lúc 05:05, 11:05, 17:05 và giữ active device lock đúng lúc Task Scheduler kích hoạt trigger, làm hủy reboot cả ca (`skipped_active_device_lock`). Quy chuẩn giải quyết:
  + Safe Window của cron xen ca BẮT BUỘC đóng trước mốc reboot tối thiểu 20 phút (11:00, 17:00, 05:00).
  + Task Scheduler cấu hình retry 5 phút một lần trong khung 30 phút từ :20 đến :50 (`05:20–05:50`, `11:20–11:50`, `17:20–17:50`) để chớp thời cơ reboot ngay khi batch nhả lock. Khi reboot hoàn tất, sentinels `admin_sentinel` và `kibe_sentinel` tự động ngắt các lần trigger kế tiếp trong khung (`skipped_shift_complete`).
  + Chốt chặn an toàn 10 phút trước ca (Reboot Cutoff Deadline): Script preflight bắt buộc chặn đứng mọi lệnh reboot nếu cách giờ bắt đầu ca dưới 10 phút (`:51–:59` trước 06:00, 12:00, 18:00) với trạng thái `skipped_reboot_cutoff`, đảm bảo hệ thống và bus USB luôn sẵn sàng trước khi ca mới chạy.
- Bẫy Claim Lane Deadlock ca đêm (Night Chain): Khi watchdog chạy batch dài (ví dụ: `cron_night_tiktok_2fa_watchdog.py` chạy Reg Gmail nối tiếp Add 2FA TikTok), nếu xuất phát sát giờ ca sáng (05:05) hoặc giờ reboot (05:20), tiến trình sẽ bị SIGKILL giữa chừng trong khi đang giữ cờ `running_since`. Cờ này có TTL tới 5400s (90 phút) làm kẹt toàn bộ các lần trigger kế tiếp. BẮT BUỘC: (1) Kiểm tra thời gian còn lại trước ca sáng/reboot >= 45 phút mới cho phép claim lane; (2) Có cơ chế tự dọn cờ claim mồ côi nếu không có tiến trình con nào đang thực sự chạy.
- Bẫy Cron Watchdog đa Phase gửi dồn về Farm Alerts (Multi-Phase Watchdog Routing): Khi một watchdog chạy chuỗi gồm nhiều Phase thuộc các repo khác nhau (ví dụ: Phase 1 Reg Gmail -> Phase 2 Add 2FA TikTok trong `post_noon_chain_watchdog` hoặc `cron_night_tiktok_2fa_watchdog`):
  + CẤM: Đặt cron `deliver: telegram:<chat_id>` trong `jobs.json` rồi print báo cáo ra stdout; Hermes cron sẽ gom toàn bộ output gửi về một nhóm duy nhất (thường là Farm Alerts `-5373649734`), gây loạn thông báo và phá vỡ quy hoạch nhóm theo repo.
  + CHUẨN: Đặt cron `deliver: local` trong `jobs.json`. Trong watchdog script, tự dispatch report từng phase về đúng chat ID tương ứng (`GMAIL_REPORT_CHAT_ID = "-5139245637"`, `TIKTOK_REPORT_CHAT_ID = "-5468653590"`) qua `dispatch_report()` / `_send_telegram_text()`. Báo cáo từng phase phải độc lập và có header phân biệt rõ ràng.
- Bẫy Kích Hoạt Test Run Bắn Rác Vào Live Chat (`cronjob run` Trap):
  + CẤM: Sau khi tạo hoặc cập nhật cronjob có đích đến là channel/group Telegram thật (`deliver: telegram:...`), CẤM TUYỆT ĐỐI gọi `cronjob action='run'` để "test thông mạch". Với `no_agent: true`, việc này lập tức đẩy stdout ra nhóm của user gây spam ngoài lịch định kỳ. Kiểm thử script watchdog BẮT BUỘC chạy offline qua CLI local (`python <script>`).
  + CHUẨN Anti-Spam cho Watchdog định kỳ khi `NO_EVIDENCE`: Đối với báo cáo đối soát định kỳ (6h, 12h, 24h), khi kết quả không phát hiện vi phạm (`NO_EVIDENCE`): hoặc im lặng tuyệt đối (stdout rỗng, exit 0), hoặc nếu user muốn báo cáo liveness thì chỉ in đúng 1 dòng tóm tắt trạng thái ngắn gọn (`🛡️ [WATCHDOG] ℹ️ Không phát sinh vi phạm (N files đối soát)`). CẤM in nguyên bảng biểu / emoji wall 8 Gate rỗng làm loãng kênh alert.
- Bẫy Bulk Pre-Reservation Chặn Đứng Các Batch Khác (Bulk Lock vs JIT Lock): Khi cron phụ/xen ca (như Tool 2FA) chạy cả ngày, CẤM TUYỆT ĐỐI acquire lock hàng loạt (`status="queued"`) trước cho toàn bộ máy; việc này sẽ khóa cứng hàng chục máy trong hàng đợi làm batch chính (Upload Video) khởi chạy song song bị fail-closed `[NEEDS_USER_DECISION] ACQUIRE_LOCKS`. BẮT BUỘC dùng cơ chế Just-In-Time (JIT) Lock: tiến trình cha lập kế hoạch giãn cách không tạo lock file, từng worker con tự acquire lock khi bắt đầu và release ngay khi hoàn tất. Đồng thời khử trùng lặp machine cho launch plan nhưng gom target theo list để không làm rơi rớt account trên máy có nhiều nick.

## References

- `references/jit-lock-vs-bulk-reservation-and-cron-safety-20261025.md` — Just-In-Time (JIT) lock architecture, multi-target deduplication, and reboot safe-window coordination.
- `references/watchdog-anti-spam-and-no-evidence-discipline.md` — Anti-spam discipline: ban `cronjob run` on live channels, and collapse `NO_EVIDENCE` periodic reports to 1 line or silence.
- `references/reboot-preflight-retry-and-10m-cutoff-protocol.md` — 5-minute preflight retry cadence, sentinel idempotency, and 10-minute session deadline cutoff.
- `references/reboot-blackout-guard-and-all-day-cron.md` — validated window math, evidence checklist, and common collision pitfalls.
- `references/reboot-session-preservation-and-anti-silent-drop.md` — 60m lookback window, assistant-last tool activity detection, and anti-confabulation testing rules.
