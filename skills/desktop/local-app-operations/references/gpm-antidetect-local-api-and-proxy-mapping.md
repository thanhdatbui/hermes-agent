# GPMLogin Local REST API & Multi-Account Proxy Pool Mapping

## 1. GPMLogin Runtime & Local API Discovery (Windows)
- **Executable Location**: `C:\Users\<User>\AppData\Local\Programs\GPMLogin\GPMLogin.exe`
- **Active API Port Resolution**:
  - Do NOT hardcode default port `9495` without probing.
  - Port is dynamically configured and stored in:
    - `C:\Users\<User>\AppData\Local\Programs\GPMLogin\api_port.dat` (e.g., `19995`)
    - `C:\Users\<User>\AppData\Local\Programs\GPMLogin\local_port.dat` (`{"websocket_port": 6866, "http_port": 9996}`)
  - **Active REST API Service**: Listens on `http://127.0.0.1:19995/api/v3/*`.

## 2. API v3 Endpoints & Exact Payload Specifications
- **List Profiles**:
  `GET http://127.0.0.1:19995/api/v3/profiles`
  - Query parameters: `page` (default: 1), `per_page` (default: 50, recommend `per_page=100`).
  - Returns `{"success": true, "data": [{"id": "...", "name": "...", "raw_proxy": "...", "profile_path": "..."}]}`.
  - Note: Filter out soft-deleted / legacy profiles in DB (`profile_data.db`) vs live profiles returned by this API.
- **Get Profile Info**:
  `GET http://127.0.0.1:19995/api/v3/profiles/{profile_id}`
- **Create Profile**:
  `POST http://127.0.0.1:19995/api/v3/profiles/create`
  - **Payload Requirement**:
    - `profile_name`: String (Required, snake_case! Passing `name` or `ProfileName` will fail with SQLite `NOT NULL constraint failed: Profiles.Name`).
    - `raw_proxy`: String (Optional, e.g., `host:port:user:pass` or `http://user:pass@host:port`).
    - `group_id`: Integer or GroupName (Default: 1 / "All").
  - Returns: `{"success": true, "data": {"id": "<uuid>", "name": "...", "profile_path": "..."}}`.
- **Delete Profile**:
  `GET http://127.0.0.1:19995/api/v3/profiles/delete/{profile_id}?mode=1` (or `mode=2`)
  - `mode` query parameter is MANDATORY. Omitting `mode` fails with `INVALID_MODE`. Mode `2` removes local folder on disk.
- **Start Profile (CDP / Automation)**:
  `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
  - Returns debugging port & WebSocket address for Playwright/Puppeteer CDP connection (`RemoteDebuggingAddress`).

## 3. Account Isolation Invariant: 1 Profile per Gmail Account
- **Anti-Pattern (1 Profile Multi-Gmail)**:
  - Logging multiple Google/Gmail accounts into the same browser profile (using Google's "Add another account") creates fatal issues:
    1. *Account Linking*: Google ties all accounts together via shared IndexedDB, LocalStorage, and browser fingerprint. One banned account will drag down the rest.
    2. *OAuth Hang / Collision*: Google displays the `/AccountChooser` screen during Antigravity OAuth login, causing automated CDP scripts to mis-click or fail.
    3. *Session Flushing*: Clearing cache/cookies for one account kicks all other accounts out.
- **Golden Rule (1 Profile = 1 Gmail = 1 Identity)**:
  - Every Gmail account must have its own isolated GPM profile.
  - When assigning up to 5 accounts per proxy IP, create 5 separate profiles sharing the same proxy string, and operate them in staggered time batches.

## 4. Proxy Pool Sizing & Symmetric Batching Rules (Farm 5:1 Model)
- **Single Source of Truth for Farm Proxies**:
  - Phone farm mapping: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
  - Combined farm + admin proxy pool: `D:\OneDrive\TaadaaData\proxy_combined_pool.txt` (69 unique endpoints).
- **1 Profile : 1 Proxy Port Symmetric Foundation (Batch 1)**:
  - 15 established profiles (`01_Rua` .. `15`): Preserved 100%, mapped to Mobi 4G ports `5101`..`5117`.
  - 54 new profiles (`16` .. `69`): Mapped to remaining 17 Mobi ports (`5118`..`5138`) + 7 MikroTik Kibe ports (`10001`..`10007`) + 28 MikroTik Admin ports (`10008`..`10035`) + 2 aux ports.
- **Scaling to 5 Accounts / 1 IP without Checkpoint Collisions**:
  - Do NOT create uneven splits (e.g. 2 profiles/port wrapping mid-sequence).
  - Deploy sequentially by full pool batches across distinct calendar days:
    - **Batch 1 (Day 1)**: Profiles `01` → `69` (1 acc/port).
    - **Batch 2 (Day 2)**: Profiles `70` → `138` (2nd acc/port).
    - **Batch 3 (Day 3)**: Profiles `139` → `207` (3rd acc/port).
    - **Batch 4 (Day 4)**: Profiles `208` → `276` (4th acc/port).
    - **Batch 5 (Day 5)**: Profiles `277` → `345` (5th acc/port).
  - Isolating login operations to 1 account per IP per day guarantees zero simultaneous login triggers on Google/OAuth infrastructure.
