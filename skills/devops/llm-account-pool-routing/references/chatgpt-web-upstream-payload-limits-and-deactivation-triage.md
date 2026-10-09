# ChatGPT-Web Upstream Payload Limits, Account Deactivation Cascade & Session Recovery

## 1. Physical Payload Breaking Point (HTTP 413) & Sol Payload Guard

### Upstream Physical Thresholds (:20129 chatgpt-web)
- **<= 41,305 bytes (~40 KB)**: Response 200 OK consistently (10-15s).
- **~65 KiB (66,724 bytes)**: Hard upstream breaking point by Cloudflare/Nginx buffer `client_max_body_size` at `chatgpt.com/backend-api/conversation`. Exceeding this returns HTTP 413:
  `[413]: ChatGPT returned 413 — the request payload is too large for ChatGPT web's size limit (often hit by agentic clients like Cline/Kilo that send big system prompts and file context). Reduce the context: enable compression, trim the conversation/files, or use a smaller request.`
- **Historical Pitfall**: `closeout_gate.py` previously had `max_bytes = 512_000` (512 KB), which is nearly 8x higher than the physical breaking point, leading to catastrophic 413 drops during closeout evaluation.

### Claude CLI Two-Layer Sol Payload Guard Architecture
```text
T2 Planner ──┐                 [Layer 1: Semantic Content Budgeter]
             ├── PromptBudgeter ──► build body ──► SolTransport.send()
Closeout ────┘   (Smart Truncator)                 [Layer 2: Fail-Closed Transport]
                                                   ├── Serialize UTF-8 (ensure_ascii=False)
                                                   ├── len > 40,000 B → RAISE PayloadTooLarge
                                                   └── Send data=raw_bytes (avoids \uXXXX bloat)
```

#### Safe Constants
- `SOL_TARGET_BYTES = 32_768` (32 KiB): Target daily operating budget (leaves 20% margin for headers, escape, JSON envelope).
- `SOL_HARD_MAX_BYTES = 40_000` (40 KB): Hard ceiling at transport layer before network dispatch. Must be <= proven working limit (41,305 B).
- `MAX_RAW_READ_BYTES = 2_000_000` (2 MB): Ceiling for reading/hashing raw diffs/logs from disk (separate from send budget).

#### Smart Context Truncator Priority Policy
- **P0 (Inviolable - Never Truncate)**: System prompt, grading rubric, Patch Contract O(1), modified files list + stat summary. If P0 alone exceeds budget, fail-closed (`BLOCKED_OVERSIZE`).
- **P1 (High Priority)**: Error signatures from test/log (`Traceback`, `Error`, `FAIL`, exit codes) +- 4 lines deduplicated by normalized regex signature; hunks of "hot" files (files mentioned in stack trace).
- **P2 / P3 (Progressive Truncation)**: Secondary source files, tests, documentation. Large hunks keep head 60% and tail 40%, with middle replaced by `… [N lines elided]`.
- **Noise (Stat-only)**: `.lock`, `package-lock.json`, `*.min.js`, `dist/`, binary files are 100% stripped of content and kept as stat-only lines.
- **Truncation Manifest Header**: Whenever truncation occurs (>= L1), prepend a manifest:
  ```text
  [TRUNCATION_MANIFEST]
  level=L4 raw_bytes=142000 sent_bytes=31800 raw_sha256=a1b2c3d4
  omitted=package-lock.json(stat-only)
  NOTE: Elided content is NOT considered reviewed. If needed to conclude, return NEED_CONTEXT:<path>.
  ```

#### Serialization Invariant & Transport Contract (P0-3)
Do NOT use default `requests.post(json=...)` or unconstrained `json.dumps` with `ensure_ascii=True`. Vietnamese UTF-8 characters (2-3 bytes) expand to 6-byte `\uXXXX` sequences, and newlines expand to 2 bytes, easily doubling wire size.
- **Rule**: Serialize once using `json.dumps(body, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8', errors='replace')`, measure that exact byte slice, and send directly via `data=raw_bytes` with `headers={"Content-Type": "application/json; charset=utf-8"}`.
- **Fail-Closed Ceiling**: In `enforce()`, the maximum allowed byte length must be hardcoded: `min(calculated_max, ABSOLUTE_CEILING_BYTES - ABSOLUTE_MIN_RESERVE_BYTES)` (e.g. 40,000 - 1,024 = 38,976 B). Environmental variables must be strictly clamped with both `min_limit` and `max_limit` so negative reserves or inflated hard-max cannot bypass the physical barrier.
- **No `assert` for Config**: `python -O` strips `assert`. Configuration validation (e.g., `reserve >= hard_max`) MUST use explicit `if ...: raise RuntimeError(...)`.
- **ReDoS Prevention on Anchor Matching**: Running unanchored regexes like `\w*(?:Error|Exception)` on raw, un-sliced lines causes quadratic backtracking on long hex/minified tokens (e.g., 200 KB single lines). Always slice the line to `line[:4096]` before executing `ANCHOR_PATTERN.search()`, and remove redundant `\w*` prefixes.
- **Raw Input Hashing (C1 / Audit Trail)**: Compute `raw_sha256` and `raw_bytes` directly on the unmodified input diff/log before any normalization, truncation, or CRLF replacement, ensuring the audit trail matches `git diff | sha256sum`.
- **Adaptive Budget Allocation (`split_budget`)**: When allocating a total budget `b` for Sol High review, use `split_budget(b) -> (diff=65%, log=25%, prompt/manifest=10%)`.
- **Transparent Manifest (`format_manifest`)**: Emits `[TRUNCATION_MANIFEST]` if EITHER diff or log is truncated. Includes `diff_sha` and `log_sha` (12 hex chars).

---

## 2. OpenAI Account Deactivation Cascade (Web + Codex)

### Upstream Behavior
- When OpenAI deactivates an account (`{"kind": "AccountDeactivated", "message": "Your account has been deactivated."}` or notification email `OpenAI - Access Deactivated`):
  - **Google Account (Gmail) remains 100% ALIVE**: `myaccount.google.com` and `mail.google.com` remain functional; only OpenAI's service is terminated.
  - **Simultaneous Upstream Revocation**: OpenAI revokes BOTH the ChatGPT-Web session AND the Codex CLI OAuth token simultaneously. Calls to Codex CLI immediately fail with:
    `[401]: Encountered invalidated oauth token for user, failing request`
- **Triage & Deactivation Protocol**:
  - The moment any watchdog or probe detects `AccountDeactivated` or `invalidated oauth token`, it must immediately set `is_active = 0, test_status = 'banned'` across BOTH `chatgpt-web` AND `codex` providers in `storage.sqlite`.
  - Prune the connection from all active combos (`chatgpt-web-pool`, `gpt-web-sol`, `codex-luna`, `codex-terra`) to prevent poisoned connection selection in `p2c` / round-robin.

---

## 3. ChatGPT-Web Session Recovery Pitfalls (GPM + Playwright)

### Dual-Path Login (SSO vs ID/Pass)
- Never assume Google SSO ("Continue with Google") for all accounts. Newer accounts or batch-registered accounts use direct Email + Password (ID/Pass).
- Authoritative source: Column L (`PASS CHATGPT`) in `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`.
- When navigating to `https://chatgpt.com/auth/login`:
  1. Fill email in `input#email-input`.
  2. If password field appears (`input#password`), fill `PASS CHATGPT`.
  3. If redirected to Google SSO or SSO chooser, select matching Google account and proceed.

### Cookie Banner Pointer Interception
- The cookie consent banner (`div[data-octane-static-cookie-consent]`) overlays login buttons and intercepts pointer events, causing Playwright click actions to retry indefinitely and hit the 30s timeout.
- Always dismiss cookie consent before interacting with auth elements:
  ```python
  cb = page.locator('button:has-text("Chấp nhận tất cả"), button:has-text("Accept all"), button:has-text("Allow all"), button:has-text("Accept")').first
  if cb.count() > 0 and cb.is_visible():
      cb.click(force=True)
  ```

### Stale Token Trap in Cookie Jar
- **The Pitfall**: The Chromium profile's local cookie store retains old, expired `__Secure-next-auth.session-token` cookies even after logout or session expiry.
- **False Green Signal**: Checking `page.url` for `https://chatgpt.com/` without `/auth/` is invalid because ChatGPT renders guest views or session-expired modals on `https://chatgpt.com/`. Reading cookies blindly without checking UI state extracts an expired token.
- **Verification Rule**:
  1. Inspect DOM text: confirm neither `"Log in"`, `"Đăng nhập"`, nor `"session has expired"` / `"phiên của bạn đã hết hạn"` is present.
  2. Validate extracted token via an actual live API probe (`1+1=?` -> `2`) before setting `is_active = 1` in OmniRoute DB.
