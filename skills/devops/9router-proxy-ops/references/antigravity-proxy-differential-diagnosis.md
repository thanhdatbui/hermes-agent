# Antigravity Through 9Router: Differential Diagnosis

Use this reference when Antigravity works directly but fails only through 9Router.

## Key distinction

A per-connection/OAuth test is not proof that a real model request works. Validate both:

1. OAuth/token refresh and connection health.
2. A fresh real `ag/*` inference request through 9Router.

If direct AG succeeds while proxied AG fails, treat the provider account as provisionally healthy and investigate the 9Router AG adapter/request path before reauthenticating or adding accounts.

## High-signal evidence

For the affected request, correlate the 9Router server log with the same timestamp and connection ID. Useful sanitized signals include:

- upstream `403`, `VALIDATION_REQUIRED`, or `PERMISSION_DENIED` from `cloudcode-pa.googleapis.com`;
- successful Google token refresh immediately before the failure;
- repeated `[ProjectId]` onboarding messages such as `onboardUser done but no project_id in response`;
- the request being routed as `ag/<model> -> antigravity/<model>`.

The combination of successful refresh plus failed project discovery points to adapter state/request construction, not a dead OAuth token. Do not print tokens or full credentials.

## 9Router 0.5.55 observation

In the installed 0.5.55 server bundle, project discovery calls `loadCodeAssist`, then falls back to `onboardUser` when no `cloudaicompanionProject` is returned. It expects the project ID at `response.cloudaicompanionProject`. The observed failure mode retries five times when onboarding reports `done: true` without that field, then logs `could not fetch projectId`.

This is evidence for a differential adapter bug/compatibility issue, not proof that every Google account requires verification. Re-check the current installed version and fresh logs before changing the bundle.

## Safe investigation sequence

1. Record the exact model ID and timestamp of a fresh failure.
2. Run a direct AG request with the same account/model, if available.
3. Run a real request through 9Router; do not rely only on Test Connection.
4. Inspect sanitized logs for token refresh, project discovery, upstream status, endpoint, and selected connection.
5. Inspect the installed adapter bundle and package version; do not patch minified code until a backup and exact reproduction exist.
6. Preserve all connections and credentials. Do not bulk-disable, delete, or re-login accounts merely because the adapter returns 403.
7. If a fix is made, validate `/api/health`, authenticated `/v1/models`, and one fresh `ag/*` inference request, then compare direct versus proxied behavior.

## Common misdiagnoses

- `Test Connection` passing does not contradict a real inference 403.
- Adding more mail accounts does not repair a shared adapter bug.
- A stale Telegram/session error must not be treated as a fresh failure; correlate timestamps and send a new request.
- `active` or priority `9999` is not equivalent to successful model inference.
- Do not label the account "unverified" solely from the proxy's 403 when direct AG works; first establish whether 9Router's request differs from direct AG.
