# Direct Email + OTP Registration Hard Gates

## Trigger
Use this runbook when the operator says *reg bằng mã*, *Direct Email + OTP*, or *Zero-SSO*. A warm Gmail/GPM profile is only a mailbox transport prerequisite; it is not evidence that ChatGPT registration used OTP.

## Canary contract
1. Run an explicit OTP-only mode (for example `--otp-only`) so pre-existing ChatGPT sessions and `ALREADY_EXISTS` checks cannot short-circuit the Email → Gmail → OTP flow.
2. Search Gmail narrowly (`from:openai.com OR ChatGPT`), open the matching OpenAI message, and extract the code from the rendered message body. Never take an arbitrary six-digit number from the whole Gmail page or an unrelated snippet.
3. Save evidence at each checkpoint: submitted email, opened OpenAI message, OTP submitted, and final result/error. UI actions require immediate screenshot evidence.
4. After OTP submission, fail closed on `incorrect code`, `invalid code`, `that code didn't work`, or localized equivalents. Remove any premature success flag and preserve the error screenshot.
5. Mark `CHATGPT_READY` only after the final gate: the URL is the actual ChatGPT app (not `/auth/`) and the prompt textarea is visible. A screenshot/log line or existing session alone is insufficient.
6. If Google presents an interactive CAPTCHA/reCAPTCHA, freeze and report it with a screenshot. Do not claim that a checkbox click solved the challenge, do not loop, and choose another clean/warm profile only after operator approval.
7. If an earlier false positive wrote `CHATGPT_READY`, remove only the suffix from that account's Excel note, save atomically, and read back the exact cell before reporting.

## Known false-positive sequence
An anonymous ChatGPT page can expose a prompt textarea while also showing `Log in`/`Sign up`; it is not logged in. Conversely, a profile can have a ChatGPT session from an earlier SSO run and report `ALREADY_LOGGED_IN`; that must not count as OTP registration. The OTP can also be stale or belong to another OpenAI message, producing a visible `Mã không chính xác` after submit.

## Evidence checklist
- Log status and timestamp for the exact email.
- Screenshot path for every form/action checkpoint.
- OCR/readback of the final screen, not only the filename.
- Excel before/after note value when flags change.
- Explicit distinction: `SUCCESS` (both gates passed), `FAIL_WRONG_OTP`, `FAIL_OTP_TIMEOUT`, `FAIL_NO_PROMPT_TEXTAREA`, or `ALREADY_LOGGED_IN` (not OTP success).
