# Cockpit Local Codex + GPM OAuth Preflight

Use this reference when building a Cockpit Codex fallback from GPM profiles. It records the verified preflight pattern; it is not a guarantee that OAuth or quota will succeed.

## Verified host facts from the canary investigation

- Cockpit Tools exposes a local OpenAI-compatible sidecar at `http://127.0.0.1:60818/v1` when the desktop app is running.
- The API requires `COCKPIT_API_KEY`; never print the key or any OAuth token.
- `GET /v1/models` is the first smoke test. A successful response alone does not prove an agent-capable model is usable.
- `GET /v1/cockpit/quota` exposes pool counts and can report `stale: true`; stale quota must not be treated as fresh capacity.
- The sidecar may advertise only a synthetic/alias model such as `codex-auto-review`; test the exact model and request shape Hermes will use before adding it to `fallback_providers`.
- The sidecar manifest/config maps an API key to an explicit account list. Inspect counts and account IDs without exposing credentials.

## GPM-to-Cockpit selection gates

1. Read the authoritative GPM supervisor state and select profiles with a real `profile_id`, a live/eligible Codex session marker, and a valid current proxy mapping.
2. Cross-check the account email against the target provider's current account store. A GPM `codex_oauth_at` marker or an OmniRoute Codex row proves only that a Codex OAuth existed somewhere; it does **not** prove that the browser session can be re-authorized into Cockpit.
3. Exclude profiles with missing IDs, missing credentials/session, active profile locks, stale failure state, or a proxy that is not live. Do not launch a browser before the disk/session preflight passes.
4. Because the OAuth callback is singleton (commonly localhost port 1455), serialize OAuth attempts. Never run ten OAuth flows concurrently and never reuse a pending callback state.
5. Run exactly one canary first. Verify the callback/account identity, account appears in Cockpit, egress proxy test passes, and a local API smoke request works. Only then expand in bounded batches.

## Proxy attachment rules

- Do not infer per-account egress proxy support from binary strings alone. Confirm it through the Cockpit UI/API operation and then run the account-specific proxy test.
- Preserve the profile's existing proxy mapping; do not invent a new one or assign a shared farm port as if it were unique. If several profiles share a port, run them sequentially and record that sharing.
- A global Cockpit proxy is not equivalent to per-account egress isolation. Record which layer was actually configured.
- Never report “fake proxy is safe” or “OAuth succeeded” without a fresh account-specific response/log and, for UI actions, a screenshot checkpoint.

## Evidence checklist

For each canary, retain redacted evidence for:

- selected profile ID/email alias, proxy port, and lock status;
- pre-OAuth browser screen and post-OAuth result screenshot;
- Cockpit account list/quota response with secrets removed;
- account-specific egress-proxy test result;
- `GET /v1/models` and one mocked/minimal completion response using the exact model;
- cleanup confirmation: GPM profile closed and no stale OAuth lock/pending state.

## Stop conditions

Stop before expanding the batch if any of these occur: account mismatch, callback collision, stale quota, missing proxy proof, model-only response without tool/stream capability, CAPTCHA/checkpoint, repeated UI failure, or an OAuth operation that would overwrite an existing token. Report the concrete evidence instead of claiming partial success.

## Cockpit (:60818) Integration to 9Router & Free Account Pitfalls

- **Tích hợp vào 9Router**: Thêm Custom OpenAI Provider trong 9Router với Base URL `http://127.0.0.1:60818/v1`, API Key `COCKPIT_API_KEY`.
- **Thực tế về Model Sol**: Cockpit không có model `sol 6.1` (gọi sẽ 404). Tên hợp lệ là `gpt-6-sol` hoặc `gpt-5.6-sol`.
- **Cạm bẫy Quota Free Account**: Khi `restrictFreeAccounts: false`, Cockpit cho phép acc Free gọi Sol. Tuy nhiên mỗi request mang prompt/tool schema (~18k-26k input tokens) sẽ đốt 4-5% quota tháng của acc Free (hết sạch sau 20-25 câu).
- **Rủi ro Revoke Token**: Gọi context nặng vào flagship model qua proxy dễ bị OpenAI trả `HTTP 401 token_revoked`, khiến acc bị vô hiệu hóa toàn bộ session. Chỉ nên cấu hình acc Free gánh `gpt-5.6-luna` (0% quota) làm fallback tier, không dùng gánh dòng Sol.
