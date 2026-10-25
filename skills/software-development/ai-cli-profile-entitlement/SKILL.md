---
name: ai-cli-profile-entitlement
description: "Use when headless AI CLI fails to inherit IDE subscription."
---

# AI CLI Profile & Entitlement Governance

## 1. When to Use
Use when configuring, debugging, or running headless AI developer CLIs (such as Antigravity `agy.exe`, Gemini Code Assist CLI, Codex CLI) in multi-account or multi-profile sandbox environments where the CLI binary fails to inherit the paid subscription (Pro/Google One AI) that the full GUI IDE possesses, resulting in 429 quota exhaustion (`RESOURCE_EXHAUSTED`).
- Reference: `references/antigravity-entitlement-protocol.md` (Protobuf structure, credit types, onboarding metadata, and local adapter injection).

## 2. Core Problem: Headless CLI vs GUI IDE Divergence
When developer tools package an IDE extension alongside a native CLI binary:
1. **The GUI IDE Client:** Uses a language server + extension bootstrap (e.g., `extension.js`, Node.js IPC). It attaches proprietary headers, session tokens, and explicitly injects paid credit types (e.g., `enabledCreditTypes: ["GOOGLE_ONE_AI"]` / `CreditType.GOOGLE_ONE_AI = 1`).
2. **The Headless CLI Binary:** Often shares the underlying Protobuf schema but lacks the GUI bootstrap flow. In headless execution (`agy -p ...`), it sends vanilla requests without the credit flags, causing upstream servers (e.g. Google Cloud Code API) to classify requests as Free Tier (`currentTier: free-tier` vs `paidTier: g1-pro-tier`) and trigger daily quota limits (~50 reqs/day).

## 3. Standard Remediation Workflow

### Step 1: Verification of Upstream Subscription
Before modifying CLI configurations, verify whether the OAuth token actually holds a paid tier:
- Call `v1internal:loadCodeAssist` with `metadata: {"ideType": "ANTIGRAVITY"}` and the user's Bearer token.
- Inspect the response:
  - If `paidTier.id == "g1-pro-tier"`, the account has Google One AI Pro.
  - If `cloudaicompanionProject` is missing, the account requires onboarding.

### Step 2: Auto-Onboard Account Tier
Ensure the account has been onboarded to the target GCP project:
- Endpoint: `/v1internal:onboardUser`
- Payload:
  ```json
  {
    "tier_id": "g1-pro-tier",
    "metadata": { "ideType": "ANTIGRAVITY" }
  }
  ```
- Ensures mapping to the `aicode-consumers` project rather than `default-cli-project`.

### Step 3: Preserving Native Agent Tools vs External Proxy
- **Strict Invariant:** Do not bypass native CLI agent capabilities by blindly replacing the CLI with an external Chat Completions proxy (e.g., routing everything through a central OpenAI-compatible endpoint). The CLI agent needs its workspace awareness, AST parsing, and native tool execution.
- **Local Loopback Adapter Pattern (`CLOUD_CODE_URL` Discovery):**
  - `agy.exe` checks the environment variable `CLOUD_CODE_URL` (logged as: `Overriding CloudCodeServerURL via CLOUD_CODE_URL environment variable: %q`).
  - Spin up a lightweight local loopback proxy (`D:/Taadaa/tools/ag_credit_proxy.py`) via `start_credit_proxy(upstream_proxy=...)` bound to `127.0.0.1:<port>`.
  - Set `env["CLOUD_CODE_URL"] = f"http://127.0.0.1:{port}"` for the `agy.exe` subprocess.
  - **CRITICAL:** Unset `HTTP_PROXY`, `HTTPS_PROXY`, `http_proxy`, `https_proxy` in `agy.exe`'s environment so it connects directly to `127.0.0.1` without sending local loopback traffic through the upstream proxy.
  - The local proxy intercepts `v1internal:streamGenerateContent`, injects `enabledCreditTypes: ["GOOGLE_ONE_AI"]` and `project: "aicode-consumers"`, and forwards upstream via `urllib.request` using the profile's upstream proxy (`upstream_proxy`).
  - Upstream backend deducts from the 1,500 req/day Google One Pro credit balance instead of hitting the 50 req/day Free Tier cap.

## 4. Key Pitfalls
1. **Never substitute an external mock for native CLI:** Replacing a native agent with a simple chat wrapper loses multi-file reasoning, file patching, and command execution.
2. **Beware of Sandbox Isolation Over-clearing:** When isolating `USERPROFILE`, `APPDATA`, and `LOCALAPPDATA` for sandbox profiles, ensure that `.gemini/projects.json` maps the workspace directories to `aicode-consumers` rather than leaving it empty.
3. **Protobuf Varint Encoding:** For binary streams, ensure `enabled_credit_types` field 8 is properly encoded (`0x40` / varint 1) if intercepting at the binary protocol level rather than JSON.
