# OMP (Oh My Pi) Multi-Profile Sandboxing & Dual-Routing Architecture

## Overview
When orchestrating `@oh-my-pi/pi-coding-agent` (`omp`) across multi-account LLM pools (e.g. 22 Pro accounts) alongside or as an alternative to `agy cli`:
1. `omp` natively supports profile isolation via `--profile <name>` or `OMP_PROFILE=<name>`.
2. Each profile stores its SQLite state in `~/.omp/profiles/<name>/agent/agent.db` and custom models in `~/.omp/profiles/<name>/agent/models.yml`.

## Critical Pitfalls & Discoveries

### 1. The Global `install-id` Correlation Leak
- **Issue**: In `@oh-my-pi/pi-utils/dirs.ts` (`getInstallId`), `~/.omp/install-id` is explicitly anchored to the base config root `~/.omp/install-id` and shared across ALL profiles regardless of the active profile name.
- **Risk**: Google and telemetry servers receiving requests across multiple accounts can correlate all accounts to the exact same installation UUID.
- **Remediation**: Sandboxed runner scripts (like `omp_cli.py`) MUST isolate the environment root (`USERPROFILE`, `HOME`, `APPDATA`, `LOCALAPPDATA`, `TEMP`) per profile, or populate isolated `install-id` files inside each profile directory.

### 2. OAuth Client ID Cryptographic Mismatch
- **Issue**: Google Antigravity tokens in `agy_profiles` (generated via `agy.exe` / Google Gemini CLI) are issued for Client ID `681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com`.
- `omp`'s `google-antigravity` native provider expects tokens issued specifically for Client ID `1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com` against `daily-cloudcode-pa.googleapis.com`.
- **Symptom**: Injecting `agy`'s `oauth_creds.json` into `omp`'s `agent.db` produces `401 UNAUTHENTICATED` (`Request had invalid authentication credentials`).
- **Rule**: Never cross-inject raw OAuth tokens between different Client IDs. Tokens must either be obtained via `omp login google-antigravity` directly or routed via the local proxy layer.

### 3. Headless OAuth Execution & `stdin closed`
- **Issue**: `omp login` relies on Node.js `readline` on `process.stdin`. When spawned from headless subprocesses without an allocated TTY / conhost, `stdin` receives an immediate EOF or broken pipe.
- **Symptom**: `omp` cancels the login loop immediately with `Login cancelled: stdin closed` and shuts down the loopback listener at `127.0.0.1:51121/oauth-callback`.
- **Fix**: Launch `omp login` within an interactive PTY or a native Windows console (`start cmd.exe /c "omp --profile <name> login google-antigravity"`).

### 4. Dual-Route Architecture (`omp_cli.py`)
To ensure high availability across multi-account pools:
- **Primary Route**: Check `~/.omp/profiles/<name>/agent/agent.db`. If native `google-antigravity` credentials exist, route directly to `google-antigravity/<model>`.
- **Fallback Route**: If native credentials are not yet authenticated, seamlessly route through the local proxy at `127.0.0.1:20129` (`omniroute/antigravity/<model>`) with `NO_PROXY=127.0.0.1,localhost`.
- **Concurrency & Lease**: Enforce file-based lease locks with PID liveness checks (`OpenProcess` / `os.kill(pid, 0)`) and auto-rotation on 429 / `RESOURCE_EXHAUSTED` responses.
