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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
