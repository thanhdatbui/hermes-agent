# Cron/watchdog report triage

Use this reference when a scheduled GPM watchdog posts an aggregate result.

## Reporting contract

- Treat the message as an operational report, not as a request to retry, stop, or edit the cron job.
- Preserve counts and safety skips exactly as reported.
- Keep categories distinct: completed, failed, proxy-limit constrained, and deferred because another farm cron owns the device.
- Do not infer the cause of an individual failure from aggregate counts. Obtain structured per-account error evidence before retrying.

## If follow-up is requested

1. Inspect the exact cron job by its job ID with the cron manager.
2. Verify script, schedule, delivery target, enabled state, and declared workdir from job metadata.
3. Prefer scheduler metadata and the declared path over broad filesystem searches.
4. Only then decide whether a job change or a targeted retry is warranted.

## Safety boundary

A report such as “39 succeeded, 1 failed, 14 safely deferred” is sufficient for status reporting but not for root-cause diagnosis. Do not claim the failed account is transient, proxy-related, or an application error without corresponding evidence.
