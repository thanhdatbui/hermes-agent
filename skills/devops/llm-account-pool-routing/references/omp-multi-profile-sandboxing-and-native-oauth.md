# OMP (Oh My Pi) Multi-Profile Sandboxing & Native Antigravity OAuth

## Overview
When orchestrating `@oh-my-pi/pi-coding-agent` (OMP) alongside or in comparison with Antigravity CLI (`ag_cli.py`), evaluating models through local proxy bridges (e.g. OmniRoute) introduces serialization overhead and latency (~15-20s penalty). To ensure direct, fair, 1:1 comparison and safe multi-account operations, OMP must be run with per-profile sandboxing and native OAuth credentials.

---

## 1. Multi-Profile Isolation & Anti-Fingerprinting (Dirs & Install ID)

### The Shared `install-id` Leak Pitfall
In `@oh-my-pi/pi-utils/src/dirs.ts`, `getInstallId()` defaults to reading and persisting `~/.omp/install-id` anchored to the base config root.
- If multiple profiles run under the same host `USERPROFILE` / `HOME`, every profile shares the exact same UUID.
- Google backend and telemetry can correlate all accounts to a single machine/instance (Sybil correlation).

### Sandboxing Environment Variables
To ensure complete isolation of cache, config, logs, and installation identity across profiles (`acc_01` .. `acc_22`):
```python
profile_dir = os.path.join(OMP_PROFILES_DIR, profile["name"])
appdata_roaming = os.path.join(profile_dir, "AppData", "Roaming")
appdata_local = os.path.join(profile_dir, "AppData", "Local")
temp_dir = os.path.join(profile_dir, "Temp")

for path in (appdata_roaming, appdata_local, temp_dir):
    os.makedirs(path, exist_ok=True)

env["USERPROFILE"] = env["HOME"] = profile_dir
env["APPDATA"] = appdata_roaming
env["LOCALAPPDATA"] = appdata_local
env["TEMP"] = env["TMP"] = temp_dir

# Strip host secrets to prevent environment leakage
for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"):
    env.pop(var, None)
```
*Note on Subprocess Command:* When `USERPROFILE` is already sandboxed into `OMP_PROFILES_DIR/<name>`, calling `omp --profile <name>` will cause OMP to resolve paths as `.omp/profiles/<name>/.omp/profiles/<name>`. To avoid nested path doubling when `USERPROFILE` is relocated, invoke Bun directly:
`[bun_path, cli_js_path, "--model", model, "-p", prompt]`

---

## 2. OAuth Client ID Incompatibility & Token Structure

### Why Token Copy from Antigravity CLI Fails (HTTP 401)
- Tokens in Antigravity IDE (`.gemini/oauth_creds.json`) are minted under Google's internal Antigravity IDE client ID.
- OMP connects using its own registered OAuth Client ID (`1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com`).
- Attempting to pass an Antigravity IDE access token with OMP's client identity results in `401 Unauthorized / Token Mismatch`.

### OMP `agent.db` SQLite Schema
Credentials in OMP live in SQLite at `<profile>/agent/agent.db` (and `.omp/agent/agent.db`):
- Table: `auth_credentials`
- Columns: `id`, `provider`, `credential_type`, `data`, `disabled_cause`, `identity_key`, `created_at`, `updated_at`
- For provider `google-antigravity`, `credential_type` must be `"oauth"`.
- `data` JSON schema:
  ```json
  {
    "refresh": "<refresh_token>",
    "access": "<access_token>",
    "expires": 1792545696624,
    "email": "<account_email>",
    "projectId": "default-gemini-project",
    "authorizedAt": 1792542097624
  }
  ```
- `expires` MUST be epoch milliseconds (`time.time() * 1000 + expires_in * 1000`). If expired by even 1ms, OMP skips the token or raises `OAuth token expired before request`.

### Refreshing Tokens Headlessly
To refresh an expired OMP grant programmatically without interactive browser stdin:
```python
import urllib.request, urllib.parse, json, base64

client_id = base64.b64decode("MTA3MTAwNjA2MDU5MS10bWhzc2luMmgyMWxjcmUyMzV2dG9sb2poNGc0MDNlcC5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbQ==").decode()
client_secret = base64.b64decode("R09DU1BYLUs1OEZXUjQ4NkxkTEoxbUxCOHNYQzR6NnFEQWY=").decode()

data = urllib.parse.urlencode({
    "client_id": client_id,
    "client_secret": client_secret,
    "refresh_token": refresh_token,
    "grant_type": "refresh_token"
}).encode()

req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
with urllib.request.urlopen(req) as resp:
    res = json.load(resp)
    # Returns: access_token, expires_in (3599s)
```

---

## 3. Concurrency, Lease Locks & State Race Safety

When managing 20+ profiles across parallel agent runners (`ag_cli.py`, `omp_cli.py`):

1. **Lease Timeout & Dead Process Recovery:**
   - Setting lease timeout to 300s when tasks can take up to 1500s creates premature release where competing processes hijack an active profile.
   - Set `PROFILE_LEASE_TIMEOUT = 1800` (30 min).
   - Only allow early stealing if `psutil.pid_exists(pid) is False`.
   - On release (`release_profile_lock`), verify that the lock file's `pid == os.getpid()` so a delayed process never removes another worker's lock.

2. **Atomic State File Replacement:**
   - Never write to a static `.tmp` filename (e.g. `pool_state.json.tmp`) because concurrent processes will collide.
   - Use unique atomic temporary files:
     ```python
     def unique_temp_path(path):
         return f"{path}.{os.getpid()}.{time.time_ns()}.tmp"
     ```
     Write to `unique_temp_path(path)` and commit via `os.replace(temp_file, target_file)`.

3. **Proxy Credential Masking:**
   - Always sanitize output from `pool-status` using regex:
     `re.sub(r"(://)[^/\s:@]+:[^/\s@]+@", r"\1***:***@", proxy_str)`
