# Batch failure evidence and state classification (2026-08-22)

## Purpose
Use after `_run_all_targets.py` returns a mixed result and the user asks to see failed-machine screenshots. A non-zero batch exit is only an aggregate status.

## Reproduction from the session
Run artifact:
`D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\20260822-173853`

Read, in order:
1. `all_results.json` — identify each target and its `result_json`.
2. Each failed target's `stdout.log` — find the last STOPPED line and every screenshot path emitted immediately before it.
3. If the emitted proof is unavailable, stale, or does not match the current device state, take a read-only `adb exec-out screencap -p` for that exact serial. Do not tap or retry merely to obtain evidence.
4. Analyze each image before sending it. Send one standalone `MEDIA:<absolute-path>` line per image.

## State classification learned
- **STT 34** (`ce031603b3158b0b02`): the run passed VPN preflight, reached the email method, then failed to find the email-entry screen after repeated email/username selector attempts. The later current screenshot showed TikTok Profile `@truong.thuy950` with a sort popup, not the historical failure screen. Report both states separately; do not claim the current screen is the failure UI.
- **STT 75** (`ce011711d4cd802905`): the run passed VPN preflight, entered `RubiPrusko04591@hotmail.com`, detected the address as an existing TikTok account, received OTP, and stopped while waiting for a password `EditText`. The current screenshot showed the OTP screen with code cells and `Gửi lại mã`; this is an existing-account login/verification state, not proof of a new registration password failure.

## Guardrails
- Existing-account detection changes the branch to login/OTP; it must not be reported as a fresh registration that merely “missed password”.
- Historical log screenshot and current screenshot are different evidence types. Label them `failure-log state` and `current state`.
- Never send a path as prose instead of a native media line.
- After evidence collection and classification, stop and await the user's instruction; no blind retry, manual tap, or code change.
