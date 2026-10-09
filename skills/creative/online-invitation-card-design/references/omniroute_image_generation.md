# OmniRoute Image Generation Provider Matrix (:20129)

Overview of image generation behaviors across different providers on local OmniRoute (`http://127.0.0.1:20129/v1/images/generations`).

## 1. Antigravity (`antigravity/gemini-3.1-flash-image`) — [RECOMMENDED]
- **Protocol**: Google Cloud Code internal API (`v1internal:generateContent`).
- **Auth**: Automated rotating OAuth tokens from Antigravity pool.
- **Speed**: Extremely fast (< 5 seconds).
- **Output**: Base64 JPEG/PNG directly in response (`data[0].b64_json`).
- **Quota Architecture Invariant (CRITICAL)**: In OmniRoute (`storage.sqlite`), all 116+ `antigravity` OAuth connections share the identical Google Cloud Project (`project_id: "aicode-consumers"`). Google Cloud Code enforces image generation quotas **per GCP Project**, NOT per individual Gmail account. Once the project quota is exhausted (`HTTP 429: Resource has been exhausted on this model. Your quota will reset after XhYm`), rotating across 100+ Gmail accounts will still return 429 because they all point to `aicode-consumers`. Do not waste turns rotating accounts on 429.
- **Why Custom GCP Projects Cannot Replace `aicode-consumers`**: User-created projects at `console.cloud.google.com` will fail with `403 PERMISSION_DENIED: Cloud Code Private API has not been used in project ... before or it is disabled`. The `cloudcode-pa.googleapis.com` service is an unlisted Google-internal private API that cannot be enabled in the public GCP API library. The Antigravity image endpoint is strictly hard-coupled to Google's internal `aicode-consumers` envelope.
- **The Proxy Egress Leak in `imageGeneration.ts`**: In `OmniRoute/open-sse/handlers/imageGeneration.ts` (around line 997), `handleGeminiImageGeneration` calls Node native `fetch(url, ...)` directly without wrapping through `resolveProxyForConnection` or `proxyFetch`. While chat completions route cleanly through per-account proxies (Mobi 5101, 5102...), image generation traffic egresses directly from the host machine's home IP. Google's anti-abuse engine detects rapid high-detail image requests originating from a single IP address against `aicode-consumers`, triggering an IP/Project rate limit block.
- **OmniRoute Image Sibling Rotation Limitation**: In `src/sse/services/imageCredentialRetry.ts` (line 113), sibling account rotation only triggers if `status === 401 || retryable === true`. When Antigravity returns 429 or 403, `isAuthFailure` is false, causing OmniRoute to return the error immediately without attempting fallback accounts.
- **Best Use**: Card backgrounds, Pixar 3D characters, watercolor illustrations, baby themes.
- **Prompt tip**: If generating a card background for text overlay, always append: `empty center space, no text, no letters, no words`.

## 2. OpenAI Codex (`codex/gpt-5.6-luna`, `codex/gpt-5.6-sol`) — [INCOMPATIBLE FOR IMAGES]
- **Protocol**: Codex CLI backend (`https://chatgpt.com/backend-api/codex/responses`).
- **Status / Limitation**:
  - `gpt-5.6-sol`: Explicitly rejected upstream: `"The 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account."`
  - `gpt-5.6-luna`: Upstream OpenAI endpoint is designated for code/terminal tools (`originator: codex_cli_rs`). When OmniRoute injects the `image_generation` tool, OpenAI strips the tool from execution (`tools: []`) and returns an empty text stream. OmniRoute surfaces: `"Codex completed without producing an image_generation_call — the model may have declined the tool"`.
  - Free plan accounts frequently hit 429 quota exhaustion (`usage_limit_reached`).

## 3. ChatGPT Web (`chatgpt-web/gpt-5.5`, `chatgpt-web/gpt-5.6-sol`) — [HIGH RISK / FREQUENT BLOCK]
- **Protocol**: Browser-cookie bridge via TLS impersonation / proxy pool.
- **Status / Limitation**:
  - Web requests to `chatgpt.com/backend-api/f/conversation` for image generation frequently time out (> 180s) or fail with HTTP 403 due to Cloudflare Sentinel / Turnstile bot protection requiring interactive browser challenge completion.
  - Accounts in the pool frequently transition to `banned: ChatGPT blocked the request (Sentinel/Turnstile required)`.
