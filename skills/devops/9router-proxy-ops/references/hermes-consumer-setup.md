# Hermes consumer setup against a remote 9Router

Use this when a second Windows machine (for example Admin) must use the 9Router instance hosted on Kibe.

## Separate the three layers

1. **Hermes app installation:** the consumer may already have the Hermes app installed. Do not reinstall it because a Git repository pull fails.
2. **Hermes repository checkout:** repo remotes and local dirty files affect `git pull`, not whether the installed app can run.
3. **Remote API path:** independently verify the LAN URL, active API key, and model endpoint.

## Safe setup sequence

1. Keep the Kibe-hosted endpoint as `http://<kibe-lan-ip>:20128/v1`.
2. Use a real active key already registered in Kibe 9Router `apiKeys`; a dummy placeholder is rejected by remote API middleware.
3. Reusing Kibe's currently active key is valid when the operator explicitly chooses it. A separate key is recommended only for independent revocation, not required for connectivity.
4. Set Hermes config through the CLI (`hermes config set ...`), not by hand-editing `config.yaml`.
5. Verify with a real authenticated `GET /v1/models` request before claiming the Admin consumer is connected.
6. Only after connectivity is proven, sync skills/config. Keep credentials, session databases, logs, and runtime state host-local; never copy them through OneDrive or commit them.

## Common mistakes

- Do not use `localhost` in the Admin config: it points to Admin, not Kibe.
- Do not infer that a `git pull` remote error means Hermes is uninstalled.
- Do not call a placeholder `***` key a working configuration.
- Do not expose the full key in chat, screenshots, OneDrive, or repository files.
- If the consumer repo has unrelated dirty files, preserve them; do not reset, stash, or commit them without explicit scope.

## Acceptance evidence

A connection is proven only when the Admin-side authenticated request returns model IDs (for example `gpt-5.6-luna`), and the Hermes configuration reports the intended custom provider. A successful environment-variable assignment alone is not sufficient.
