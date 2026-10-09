# Hotmail GPM Login: Password vs OAuth and Farm Mapping

## Core correction
For a Hotmail account represented as `email|password|refresh_token|client_id`, the GPM browser session is established with **email + password at `https://login.live.com`**. The Microsoft `refresh_token` and `client_id` are auxiliary: use them to read mailbox/OTP through Microsoft Graph if a normal login challenge requests a code. Do not block merely because there is no Microsoft OAuth browser-session injector.

The Android Outlook canonical flow (`D:\Taadaa\Hotmail\flows\hotmail_login.py` and `scripts\hotmail_list_runner.py`) is separate from the GPM Playwright/CDP flow. Do not confuse its absence of GPM support with inability to perform a standard password login in GPM.

## Mapping contract
For Hotmail farm accounts, resolve ownership from:

1. `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`, sheet `Tài Khoản`: Hotmail -> S7 machine and serial.
2. `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`, sheet `Proxy`: machine -> raw proxy/port.

Never infer machine ownership from the order of `hotmail_input.txt`, and do not fall back to `gmail_clean_v2.xlsx` when the target is absent there.

## Execution contract
- Profile name: `<machine:02d> - <email> - <proxy-port>`.
- Pass `raw_proxy` at profile creation, before browser start.
- Process one account at a time; stop/close in `finally`.
- Verify proxy egress and login/session URL; capture pre/post screenshots for UI evidence.
- If an unhandled SMS/app lock/reCAPTCHA challenge appears, mark only that account BLOCKED with screenshot and continue; do not invent a bypass.
- A worker-created runner is not execution evidence. Run it, capture exit code/stdout, read its report, and reconcile GPM profile inventory before reporting DONE.

## Verified mapping example from the session
- `vjorandrea1961@hotmail.com` -> M02 -> proxy 5102
- `yazmillanofer@hotmail.com` -> M04 -> proxy 5104
- `sayaertluis@hotmail.com` -> M08 -> proxy 5108
- `jericiordekias@hotmail.com` -> M09 -> proxy 5111
- `djricharalfr@hotmail.com` -> M10 -> proxy 5112

Keep credentials and tokens out of reports and chat.