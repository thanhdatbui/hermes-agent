# Cron/watchdog report triage

Use this reference when a scheduled GPM watchdog posts an aggregate result.

## Reporting contract

- Treat the message as an operational report, not as a request to retry, stop, or edit the cron job.
- Preserve counts and safety skips exactly as reported.
- Keep categories distinct: completed, failed, proxy-limit constrained, and deferred because another farm cron owns the device.
- Do not infer the cause of an individual failure from aggregate counts. Obtain structured per-account error evidence before retrying.
- **Explain shorthand instead of parroting**: When presenting or explaining the report (e.g., if the user says "chưa hiểu report" or asks for status), DO NOT just echo the raw bullets. Decode domain terms clearly:
  - `✓ N | ✗ M`: Total successful vs failed logins accumulated across shifts.
  - `proxy_limit 2/port/ngày`: Hard safety throttle (max 2 logins per proxy port/day) to prevent Google IP flagging.
  - `Bỏ qua an toàn: N acc`: Device lock deferrals — accounts whose assigned phones are busy running TikTok feed or Avatar upload crons; deferred to next shift to avoid collision.
  - `Antigravity Pool: N accounts LIVE`: Total ready accounts actively serving LLM routing on OmniRoute (:20129).
  - `Profile sẵn Google Session: N accounts`: GPM profiles with valid Google session cookies (`SID`, `SSID`, `HSID`) ready for zero-prompt OAuth.
  - **Action verdict**: Always conclude with a clear verdict on whether the shift finished safely and whether any user intervention is required.

## If follow-up is requested

1. Inspect the exact cron job by its job ID with the cron manager.
2. Verify script, schedule, delivery target, enabled state, and declared workdir from job metadata.
3. Prefer scheduler metadata and the declared path over broad filesystem searches.
4. Only then decide whether a job change or a targeted retry is warranted.

## Safety boundary

A report such as “39 succeeded, 1 failed, 14 safely deferred” is sufficient for status reporting but not for root-cause diagnosis. Do not claim the failed account is transient, proxy-related, or an application error without corresponding evidence.
