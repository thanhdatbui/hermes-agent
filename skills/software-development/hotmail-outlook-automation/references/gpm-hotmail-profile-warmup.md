# GPM Hotmail profile warm-up

## Durable lessons

- Treat Hotmail trust on a GPM browser profile separately from mailbox age on Android/farm. A newly seeded profile can be rejected when it immediately opens `account.live.com/password/change`.
- Before nurture, verify the mapped GPM profile has a live Gmail session. The Gmail nurture preflight checks Google cookies `SID`, `SSID`, `HSID`, and `SAPISID`; missing cookies means skip nurture.
- Seed Hotmail on the machine-mapped profile, preserve KMSI/session cookies, open Outlook once as readback proof, then persist `profile_id`, mapped Gmail identity, `first_seeded_at`, and `eligible_change_pass_date`.
- Automatic change-password selection must require tracker `status == NURTURING` and `today >= eligible_change_pass_date`. An explicit canary may bypass that automatic filter, but must still capture pre-submit/post-submit evidence and treat Microsoft's temporary-service/risk page as not changed.
- Never infer success from a filled form or process exit code. Confirm the post-submit page and workbook/state readback; retain the old password after a Microsoft temporary-service/risk error.

## Session evidence pattern

- Outlook readback proof was captured after login on the mapped GPM profile and showed the account mailbox and TikTok messages.
- The profile was mapped to a Gmail-named GPM profile, but its Google session-cookie preflight was empty; this is a hard signal that Gmail nurture/login must occur before claiming the profile is actively nurtured.
- Keep the Hotmail nurture tracker separate from the changed-password tracker. Do not mark an account changed merely because it has been seeded or because the script reached the change form.
