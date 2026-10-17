# Native HTTP web-provider migration

Use this as a compact runbook when a browser-backed provider is moved to a direct HTTP protocol.

## Protocol contract

- Preserve the existing OpenAI adapter boundary and connection-scoped proxy context.
- Load the authenticated web page first and extract bounded session/build tokens.
- Send the provider RPC as form-encoded data with the current cookie jar, origin, referer, user-agent, and any provider-specific authorization hash.
- Reuse the existing response-envelope parser and output format. If native streaming is unavailable, preserve the adapter's pseudo-SSE behavior rather than silently changing callers.
- Return an explicit unsupported response for unimplemented modes such as image generation.
- Persist rotated authentication cookies only through the existing refresh callback; never print cookie values.

## Test contract

Focused tests should mock `globalThis.fetch` with deterministic page HTML and RPC response bodies. Assert:

- page GET occurs before RPC POST;
- token/build-label extraction is bounded and missing auth fails closed;
- form fields and essential headers are present without exposing secrets;
- abort/timeout and non-2xx responses map to the provider's established errors;
- JSON and pseudo-SSE output remain compatible;
- unsupported capabilities do not return a false success.

Remove or rewrite old browser-launch mocks. A stale Playwright test commonly turns a deliberate HTTP-path change into misleading `401`, `502`, or missing-browser status failures.

## Verification evidence table

| Gate | Required evidence |
|---|---|
| Static | focused test output, typecheck exit 0, scoped `git diff --check` |
| Build | complete build exit 0; a generated build directory alone is insufficient |
| Runtime | service health response after reload |
| Canary | one real pool request with HTTP status 200, latency, resolved model, and exact marker |
| Blocked state | raw status/body and reason, such as pre-dispatch all-targets-skipped or stale process |

A healthy endpoint without a successful model response is not a canary pass. If the first canary is blocked by a stale process or all-targets-skipped filter, reload the actual service once and issue one bounded retry; do not loop in the dark.

## Safety and scope

- Keep unrelated dirty files untouched and report them separately.
- Do not use live credentials in fixtures or logs.
- Do not bypass the production proxy to make a canary pass.
- Distinguish a legacy-test mismatch from a real production regression by checking whether the test still assumes the removed browser path.
