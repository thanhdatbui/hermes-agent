# Reboot blackout guard: validated pattern

## Requirement
Keep an intentionally all-day watchdog on its existing schedule (for example, `*/15 * * * *`) while preventing it from starting close to fixed host reboots. Do not solve this by pausing the cron or changing it to night-only.

## Window math
For reboot times 05:20, 11:20, and 17:20, the validated conservative buffer is 15 minutes before and after:

- 05:05 through 05:34
- 11:05 through 11:34
- 17:05 through 17:34

A safe-window predicate should return false in these ranges and retain all existing feed/cache/device-lock guards.

## Verification evidence
- Read the actual cron schedule and verify it remains unchanged.
- Check the reboot log and system boot time.
- Identify active lock-holder PID, process creation time, parent PID, and full command line when a reboot is skipped.
- Add focused boundary tests: first and last blocked minute for each window, plus a just-outside minute.
- Run the focused test file and report its real pass/fail output.
- Sync the verified source to the Hermes runtime copy and shared deployment only after tests pass.

## Pitfalls
- A job named “night” may still be configured to run every 15 minutes all day; inspect the actual schedule.
- A skipped reboot may be intentional lock safety, not a scheduler failure.
- Do not claim a fix from a test alone: schedule, runtime deployment, and live evidence must agree.
