# Hotmail → GPM → ChatGPT lineage contract

## Canonical mapping
- Farm ownership comes from `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`, sheet `Tài Khoản`.
- Resolve `GMAIL` → `Máy` → `device ID`, then resolve the proxy from `PROXYgandienthoai.xlsx`.
- Do not infer machine assignment from the order of `hotmail_input.txt`, and do not treat `gmail_clean_v2.xlsx` as authoritative when the Hotmail row is absent there.
- One Hotmail gets one dedicated GPM profile. Assign proxy at profile creation and name it `<machine:02d> - <email> - <proxy-port>`.

## Credential roles
- Hotmail password is for `login.live.com`.
- `refresh_token` and `client_id` are auxiliary mailbox/OTP credentials; they are not required to establish a normal GPM browser login.
- ChatGPT registration is direct email + OTP, never Google SSO.
- Store a dedicated `PASS CHATGPT` field separately from `PASS MAIL`. If the user explicitly wants continuity, initialize `PASS CHATGPT` from the current mail password only when empty. The ChatGPT resolver must prefer `PASS CHATGPT` and fail closed when it is missing; never silently fall back after the field exists.
- A later Hotmail password change to match `PASS CHATGPT` is a separate explicit operation, not part of registration.

## Execution and evidence
- Use the exact GPM profile ID; email-only discovery can select duplicate or wrong profiles.
- After authorization, execute the existing runner rather than only preparing it.
- Verify exit code, exact profile ID/name/proxy, session state, report path, and fresh screenshots.
- A zero exit code or filename is not success proof; final success requires a fresh ChatGPT surface with a logged-in artifact.
- If a script is Gmail-only, record the hardcoded filter/CLI limitation and dispatch a focused compatibility patch. Do not fabricate success or create alternate profiles.

## Session lessons
The common failure mode was confusing Microsoft OAuth-token availability with the ability to log into Hotmail in a browser. Correct handling is password login first, with Graph token used only for mailbox OTP retrieval. Another failure mode was selecting the first five lines of a source list instead of resolving each account through the farm workbook.
