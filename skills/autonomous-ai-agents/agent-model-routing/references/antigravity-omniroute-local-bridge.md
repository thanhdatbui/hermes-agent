# Antigravity GUI vs Hermes/OmniRoute integration

Use when a user asks to connect the desktop Antigravity app to Hermes or to route a coding/review task through Antigravity.

## Verified architecture pattern

- The desktop Antigravity Electron app may expose localhost CDP/UI ports (for example `60450` for Chromium DevTools and adjacent internal ports). Those ports are for desktop UI/debugging, not the normal Hermes model transport.
- Hermes model calls should use the configured OpenAI-compatible OmniRoute endpoint (`/v1/chat/completions`) and the provider/model IDs already configured in Hermes (for example `ag-gemini-pool-3`, `ag-sonnet`, or `ag-opus`). Do not infer that a running GUI means Hermes is connected; verify the model gateway separately.
- A local HTTP smoke request is the authoritative connectivity check: send a harmless short prompt with `stream: false`, a bounded timeout, and no credentials in output. Record HTTP status, routed model, response, and latency.
- OAuth onboarding is a separate path from inference. Existing scripts may use OmniRoute endpoints such as `/api/oauth/antigravity/authorize` and `/api/oauth/antigravity/exchange`; never enter passwords, tokens, CAPTCHA answers, or recovery codes from an autonomous session.

## Safe procedure

1. Read the active Hermes provider/model configuration; do not edit `config.yaml` by regex/text replacement.
2. Verify the OmniRoute endpoint with one short smoke request and a timeout appropriate to the measured route latency. The first response may be slow because the pool rotates/upstreams retry.
3. If the requested `ag-*` model already resolves and returns HTTP 200, no additional GUI-to-Hermes wiring is needed.
4. Use the desktop CDP only for an explicitly requested UI task; it is not a substitute for the model API.
5. Keep provider credentials in the router; client config should reference the local router and its configured auth mechanism, never upstream secrets.

## Failure classification

- HTTP 200 with a response proves the gateway route, not that every Antigravity account is healthy.
- Timeout is transport evidence only; do not call it a model-quality failure or rewrite routing after one slow request. Retry with a changed timeout or inspect router health.
- A CLI/model listing proves catalog visibility, not successful inference. Always perform the smoke request.
- If OAuth/account setup is missing, report BLOCKED with the exact missing prerequisite; do not silently launch UI automation or ask the user to paste secrets into chat.
