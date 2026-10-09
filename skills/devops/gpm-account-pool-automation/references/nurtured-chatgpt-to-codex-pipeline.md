# Nurtured ChatGPT → Codex pipeline (2026-09-25)

## Verified inventory
- Gmail nurture cron: `gpm-gmail-nurture-watchdog`, runtime `C:/Users/Kibe/AppData/Local/hermes/scripts/cron_gpm_gmail_nurture.py`.
- Nurture state: `D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json`.
- State fields observed: `status`, `last_nurtured`, `last_nurtured_iso`, `profile_id`.
- GPM login watchdog: `post-evening-gpm-login-watchdog`; it already reads nurture state, checks profile/session readiness, proxy limits, idle windows, and device locks.
- Direct ChatGPT reg: `D:/Taadaa/GPM auto/scripts/chatgpt_gpm_direct_reg.py`; success marker is `CHATGPT_READY` in the master workbook.
- Existing Codex OAuth workers: `batch_codex_oauth_standalone.py`, `run_single_codex_worker.py`, and phone verification helper `codex_5sim_auto_verify.py`.

## Integration contract
1. Do not create a second nurture cron. Reuse `gpm_gmail_nurture_state.json` as the source of truth.
2. Registration and OAuth are separate stages. Finish Direct Email + Gmail OTP registration and record `CHATGPT_READY`; do not chain Codex OAuth in the same browser transaction.
3. A Codex candidate must satisfy all gates: `CHATGPT_READY`; nurture age >= the configured policy (default must be explicit, e.g. 24h or 48h); GPM profile/session still valid; not already active in OmniRoute Codex; machine/proxy/device-lock preflight passes.
4. OAuth must run as a bounded worker/job with per-profile cleanup and evidence. Never dispatch the entire nurture batch into OAuth blindly.
5. Phone verification is fail-closed. For VN/+84 traffic, use an approved real Farm SIM; never silently use a foreign virtual number on a VN proxy. If phone verification or captcha is ambiguous, stop and report the account; do not retry in a loop.
6. Before integration, inspect the existing worker's selectors and API contract; preserve its callback polling, screenshot, timeout, and profile-stop cleanup behavior.

## Important distinction
`status == success` in nurture state means the Gmail profile was nurtured successfully; it does not by itself prove ChatGPT readiness or Codex eligibility. `CHATGPT_READY` and Codex-pool absence are independent gates.

## Evidence checklist
- Candidate email, machine/profile ID, nurture timestamps and age.
- ChatGPT readiness source (workbook/state) and OmniRoute Codex lookup result.
- OAuth callback/connection ID or a precise fail reason.
- Screenshot paths for UI checkpoints; no success claim from a worker summary alone.
