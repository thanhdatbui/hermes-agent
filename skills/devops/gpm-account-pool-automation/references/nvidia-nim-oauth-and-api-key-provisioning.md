# NVIDIA NIM API Key Provisioning via Hotmail/Google GPM OAuth

## Overview & Architecture
NVIDIA NIM (NVIDIA Inference Microservice) at `build.nvidia.com` provides 1,000 free credits per account for enterprise-grade LLM inference on H100/B200 GPU infrastructure.

Supported High-Tier Coding Models:
- `moonshotai/kimi-k3`
- `deepseek-ai/deepseek-r1` / `deepseek-ai/deepseek-v3` / `deepseek-v4-pro`
- `qwen/qwen2.5-coder-32b-instruct`
- `meta/llama-3.3-70b-instruct`

## 1. Registration & Authentication Workflow

### Pitfalls with Direct Email Sign-up
- Direct email sign-up at `https://login.nvgs.nvidia.com/v1/create-account` triggers hCaptcha puzzle challenges that require manual drag-and-drop solving.

### Fast Path: Microsoft / Google OAuth
1. Navigate to `https://build.nvidia.com/explore/discover?modal=signin`.
2. Select **"More Signup Options"** -> **"Log In With Microsoft"** (for Farm Hotmail accounts) or **"Log In With Google"**.
3. Authenticate with Hotmail password from farm storage (`taikhoan_dat_v2_updated.xlsx` / `gmail_clean_v2.xlsx`).
4. On redirect to `https://login.nvgs.nvidia.com/v1/link-account`, click **"Link Account & Log In"** or complete profile.
5. On the first successful login, navigate to `https://build.nvidia.com/<provider>/<model>` (e.g. `https://build.nvidia.com/moonshotai/kimi-k3`).
6. Click **"Get API Key"** -> **"Generate Key"** -> Copy the `nvapi-...` token.

## 2. CDP & GPM Automation Patterns
- **Base URL:** `https://integrate.api.nvidia.com/v1`
- **Authentication:** `Authorization: Bearer nvapi-...`
- **CDP Freeze Recovery:** If Playwright CDP connection hangs on NVIDIA SPA, issue standard GPM REST calls:
  1. `POST http://127.0.0.1:19995/api/v3/profiles/stop/<profile_id>`
  2. Sleep 2s
  3. `POST http://127.0.0.1:19995/api/v3/profiles/start/<profile_id>`
  4. Reconnect Playwright over fresh `remote_debugging_address`.

## 3. Upstream Router Integration (9Router / Omni)
- Group 10-20 `nvapi-...` keys into a provider pool in **9Router (:20128)** or **Omni (:20129)**.
- Set fallback / round-robin so when one key consumes its 1,000 credits, traffic transparently switches to the next account key.
