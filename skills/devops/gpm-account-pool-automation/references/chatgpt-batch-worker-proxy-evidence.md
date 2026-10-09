# ChatGPT GPM Batch: Worker/Proxy/Evidence Pattern

## Reusable manifest contract

Before execution, materialize a bounded manifest with one row per selected profile:

`email | profile_id | profile_name | raw_proxy | password_available | prior_state`

For a batch capped at `N` workers, select at most `N` rows and require unique exact `raw_proxy` values. Deduplicate both `email` and `profile_id`; a Gmail may exist in multiple GPM profiles, so profile identity must remain explicit.

## Execution

- Use the canonical direct Email + OTP runner, one command per selected email/profile.
- Run at most 5 subprocesses concurrently unless a stricter user limit applies.
- Capture each process's stderr, stdout, return code, start/end timestamps, and screenshot paths independently.
- Do not confuse a dry-run candidate list with execution evidence.
- If a wrapper times out or returns an empty summary, retry with five explicit targets rather than redispatching a broad discovery batch.

## Evidence gate

A script status such as `ALREADY_LOGGED_IN` or an Excel marker such as `CHATGPT_READY` is not final proof. Verify the exact result screenshot exists and is fresh for the run, then OCR/read it independently. Accept only visible ChatGPT artifacts such as `ChatGPT`, the prompt area (`Hôm nay bạn có tưởng gì?` / equivalent), sidebar, or profile identity.

Keep these outcomes distinct:

- `SUCCESS_CONFIRMED`: screenshot + OCR/inspection prove ChatGPT UI.
- `ALREADY_LOGGED_IN_UNVERIFIED`: script says session exists but screenshot/OCR has not been checked.
- `FAIL_PASSWORD_NOT_FOUND`: data/password-source failure; do not retry OTP blindly.
- `FAIL_OTP_TIMEOUT` / Gmail re-login / CAPTCHA / phone/manual: account-scoped blocker; preserve evidence and move to another proxy.
- `ERR_ABORTED` or wrapper exception: incomplete execution evidence; never promote to success.

## Known observed pattern

A five-target run produced two independently OCR-confirmed ChatGPT screens (`luuhuong...` and `lequynh...`), three non-success outcomes (`FAIL_PASSWORD_NOT_FOUND` for two accounts and `net::ERR_ABORTED` for one), while the wrapper failed to collect official return codes. The correct report preserved the observed statuses and explicitly marked missing return-code/OCR evidence instead of inventing it.
