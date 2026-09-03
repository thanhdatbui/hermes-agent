# CLIProxyAPI recovery and Antigravity validation

Session-derived reference for the installed CLIProxyAPI/CPAMC surface. Keep secrets out of logs and reports.

## Management layer

- Dashboard URL must use the port in the live shortcut/process, not a remembered screenshot URL.
- `remote-management.secret-key: ""` means management routes are disabled; `/v0/management/config` returns `404`.
- After setting a local management key and restarting/reloading, no-key requests return `401` and authenticated requests return `200`.
- Management Key is distinct from 9Router's dashboard password and from `/v1` client API keys.

## Recovery rules

- Inspect the shortcut target, config argument, working directory, process command line, listener, and logs before changing anything.
- Search for a prior config and backups before using `config.example.yaml`.
- If no prior config exists, use the exact installed binary's example only as a bootstrap. Preserve the configured auth directory, set the launcher-required port, and remove sample API keys. A server can be restored while auth files remain absent; report those as separate outcomes.
- If a process already owns the target port, do not start a second copy and misread its bind error as a failed recovery. Verify which process owns the port and whether the running instance has reloaded the intended config.

## Minimal smoke test

1. Query `GET http://127.0.0.1:<port>/v1/models` and select a model actually returned by that instance.
2. Send one short non-stream request to `/v1/chat/completions`.
3. Record HTTP status, response model, finish reason, and a short content prefix only.
4. Stop after one success or one clear upstream failure; do not burn quota with retries.

A catalog `200` proves only that the local proxy is serving its model list. A completion `403` containing `PERMISSION_DENIED`, `VALIDATION_REQUIRED`, or `Verify your account to continue` proves the upstream provider requires account validation. Use the validation URL embedded in the error or the provider's OAuth re-login flow; do not delete/disable the credential as a first response.

## Port sanity

Always compare the screenshot address-bar port with the actual listener and process. Similar local ports can represent different services or instances; a screenshot showing `6018` does not prove the tested service at `60818` is the same instance.
