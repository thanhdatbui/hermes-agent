# Direct Email + Gmail OTP registration lessons

## User intent
In this farm, “reg” means **Direct Email + one-time code from Gmail**. It does not mean Google SSO or merely reusing a ChatGPT browser session. A profile that opens ChatGPT already logged in is not evidence of a new registration.

## Candidate selection
Prefer a warm GPM profile with a live Google session and no ChatGPT/OpenAI cookies. Warmup success alone is insufficient: inspect both the warm-state record and profile cookies before selecting a canary.

## OTP-only mode
Use an explicit `--otp-only` mode for canaries. It must bypass every `ALREADY_LOGGED_IN` and `ALREADY_EXISTS` early return, while retaining all post-OTP validation. Never mark Excel from a pre-OTP branch.

## OTP extraction
Search Gmail with `from:openai.com OR ChatGPT`, open the matching OpenAI message, wait for its rendered body, and extract from the message body (`div.ii.gt`, `div.adn`, `div[dir="ltr"]`, or equivalent). Do not take the first six-digit number from the whole Gmail page or a stale snippet: this produced a wrong-code false success.

## Hard gates
1. After OTP submit, capture a checkpoint screenshot. If the page contains an incorrect/invalid-code message, return `FAIL_WRONG_OTP`, remove any tentative readiness flag, and stop.
2. Report success only when the URL is a non-auth `chatgpt.com` page and a prompt textarea is visible. Only then save the success screenshot and write `CHATGPT_READY`.

## Evidence and worker discipline
Treat `ALREADY_LOGGED_IN`, `ALREADY_EXISTS`, OTP timeout, wrong OTP, CAPTCHA/re-auth, and missing-prompt as distinct outcomes. Verify worker claims independently against log, screenshot OCR, and Excel readback. Keep UI evidence continuous with pre-submit/post-submit screenshots and attach the relevant `MEDIA:` path. A timed-out worker is not evidence of progress; inspect the last log/screenshot before dispatching a new contract. If Gmail shows CAPTCHA or re-auth, freeze that candidate and report it; do not blindly retry.
