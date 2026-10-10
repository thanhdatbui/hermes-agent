# Hotmail lifecycle-cron gate alignment

## Eligibility contract
For the Hotmail change-info supervisor, an account is eligible only when:

- TikTok registration succeeded: workbook `ID` and TikTok `PASS` are both non-empty.
- ChatGPT registration exists: workbook `PASS CHATGPT` is non-empty, or an equivalent trusted state marker such as `chatgpt_registered_at` is present.

Keep the independent gates for supported Microsoft domain, recovery-mail availability, 7-day soak, changed/cooldown state, device lock, and one egress IP/proxy per 24 hours.

## Important implementation detail
Remove the retired Dual-OAuth requirement from **both** locations:

1. The `WAIT_7D -> CHANGE_INFO` state-transition result.
2. The scheduler candidate filter that decides whether a `WAIT_7D` or `CHANGE_INFO` profile may run.

Removing it from only the change script does not activate the cron: the supervisor can still skip every candidate before launching the script.

## Cron preflight
Before “resuming” the job, inspect the scheduler state. The supervisor may already be enabled and running every five minutes; in that case change the gate logic rather than creating a duplicate cron job. Verify the job ID, enabled state, schedule, and next run after the change.

## Verification
Use a bounded offline check: inspect workbook headers and count eligible Hotmail rows, run `py_compile`, and run a focused supervisor eligibility/state-transition test. Do not use live GPM profiles or devices for this gate change.
