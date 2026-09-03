# Remote consumer setup: another Windows host using Kibe's 9Router

## Goal
Connect an Admin PC to the 9Router instance running on Kibe. This is a LAN service integration with authentication; a reachable TCP port alone is not proof of success.

## Safe runbook

1. **Discover, do not guess**
   - On Kibe, verify the actual LAN IPv4 address, the listener, and that 9Router is bound beyond localhost.
   - Keep the endpoint in the form `http://<KIBE_LAN_IP>:20128/v1`.
   - If Windows Firewall blocks inbound TCP/20128, add the narrowest private/domain inbound rule with elevation. Do not weaken the whole firewall.

2. **Use a real active 9Router key**
   - Remote `/v1` requests are checked against Kibe's active `apiKeys` records.
   - `***`, `dummy`, or an arbitrary placeholder does not bypass authentication.
   - Reusing the currently active Kibe key works technically if the user explicitly asks for it. A separate Admin key is preferable when independent revocation matters.
   - Never print a key, put it in Telegram, screenshots, OneDrive, a repo, or `config.yaml`. Set it through the Admin user's secret/environment mechanism. If the key was exposed in chat or an image, rotate/revoke it after testing.

3. **Set the Admin environment**
   - `SetEnvironmentVariable(..., 'User')` affects future processes; it does not reliably update the already-running PowerShell process.
   - Either open a new PowerShell after setting the User variable, or set the process variable for the current test as well.
   - Do not ask the user to paste a multi-line backtick block. Give one complete PowerShell line at a time.

4. **Authenticate from Admin**
   - Run a one-line `GET /v1/models` request with `Authorization: Bearer $env:NINEROUTER_API_KEY`.
   - Success means model IDs are returned. `Test-NetConnection` only proves TCP reachability.
   - `401 API key required`/`Unauthorized` means the key was not present in the process, is invalid/inactive, or the request header was malformed.
   - Timeout/refused means network binding, firewall, wrong IP, or service state—not a model/provider problem.

5. **Configure Hermes only after the probe passes**
   - Keep the custom provider base URL on the Kibe LAN endpoint and use the recognized key environment field for that provider.
   - A warning that `auxiliary.vision.key_env` is unrecognized means Hermes may ignore that field; do not claim vision works until a real image request succeeds.
   - Start a fresh Hermes process/session after changing environment/config and verify the actual provider/model response.

## PowerShell prompt recovery

If a pasted command leaves the shell at `>>`, press `Ctrl+C`, wait for `PS ...>`, and issue a new single-line command. Do not paste the incomplete block again. The earlier failure mode was caused by combining a truncated command with backticks; the fix is a complete one-line probe, not repeated Enter presses.

## Acceptance evidence

Report only these as success evidence:

- Admin-side authenticated `GET /v1/models` returned model IDs.
- A fresh Hermes process/session completed a test request through `custom:9router`.
- For vision, an actual image request succeeded.

Do not report success from a config write, a returned PowerShell prompt, a port check, or a guessed LAN IP alone.
