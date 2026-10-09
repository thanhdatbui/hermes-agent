# Gateway/router provenance checklist

Use for screenshots or posts claiming that a free account can call a normally unavailable model through a gateway such as Cockpit or 9Router.

## Evidence ledger

Record four columns before explaining the mechanism:

| Layer | What to capture | What it proves |
|---|---|---|
| Screenshot/UI | Exact visible model label, account label, timestamp, source | Only what the UI displayed |
| Client request | `model`, endpoint, auth class, headers with secrets redacted | What the client requested |
| Gateway resolution | alias/combo, fallback decision, selected provider/account | How the gateway routed it |
| Upstream response/log | provider, resolved model, usage, status, quota | What likely executed |

## Hypothesis matrix

- **Credential substitution:** the gateway uses a different OAuth/API credential or shared pool than the visible free account.
- **Alias/remapping:** the displayed model is a local alias that resolves to another upstream ID.
- **Fallback:** the requested model failed and the gateway silently selected a backup.
- **Entitlement gap:** an experimental/internal route accepts the request without the normal UI check; availability may be temporary and may violate provider terms if abused.
- **Actual entitlement:** upstream logs and usage show the same account and exact model ID.

Do not choose among these from a 200 response alone.

## Minimal authorized verification

1. Use a harmless short prompt and a credential/account the operator is authorized to use.
2. Run the same request directly and through the gateway.
3. Capture request body, response metadata, gateway routing log, and usage/quota record; redact tokens and account identifiers.
4. Compare `requested_model` with `resolved_model`, provider, credential/account, fallback reason, and usage.
5. Stop if the gateway refuses access, if the account is not authorized, or if the test would consume meaningful quota.

A local `401` means authentication is required. It is not evidence of model availability. A router's OpenAI-compatible API, alias support, multi-account routing, fallback, or quota tracking explains request plumbing, not entitlement.

## Reporting language

Use three headings: **Observed**, **Documented**, and **Inferred/unverified**. Preserve uncertain OCR/model names exactly (for example, write ``OCR read `sol 6.1`; canonical ID unconfirmed``) instead of guessing a nearby public model. Conclude with confidence and the single missing artifact needed to confirm the claim, usually an upstream routing log or response metadata.
