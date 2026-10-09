# OmniRoute Account Removal and Free-Replacement Evidence

Use when an operator wants one account fully removed from OmniRoute and two healthy free-tier replacements.

## Removal contract
1. Resolve the exact provider connection by email from `GET /api/providers`; record only the connection ID and non-secret status fields.
2. Enumerate every combo reference by scanning `GET /api/combos` for `models[].connectionId == target_id`. One connection can be present in multiple Pro, Free, Gemini, Claude, or legacy combos.
3. Delete with `DELETE /api/providers/<connection_id>`.
4. Verify `GET /api/providers` no longer contains the ID **and** `GET /api/combos` has zero references. A successful DELETE response alone is insufficient.

Do not mutate combos one by one when deleting the provider connection unless the API reports orphan references; deleting the canonical provider connection and then checking all references avoids leaving a live credential behind in another pool.

## Free candidate filter
Prefer candidates satisfying all of:
- `provider=antigravity`
- `isActive=true`
- `testStatus=active`
- `providerSpecificData.tier=free-tier`
- `providerSpecificData.subscriptionTier=Antigravity Starter Quota`
- non-empty `projectId` (normally `aicode-consumers`)
- no `errorCode`, `lastError`, `invalid_grant`, `VALIDATION_REQUIRED`, or restricted/Business metadata

Confirm pool membership by checking combo names after selection, not just provider metadata.

## Live evidence and interpretation
Run `POST /api/providers/<id>/test` for each selected candidate. The Antigravity test endpoint may return HTTP 200 with `valid=true`, `diagnosis.type=ok`, and a warning that its upstream probe returned HTTP 400; treat that as a credential-health confirmation, not an inference canary.

A direct inference canary returning HTTP 200 is the strongest proof of serving ability. If it returns `429` with wording like `all antigravity accounts have exhausted their quota (reset after Xm)`, classify it as temporary shared family/pool quota exhaustion. Do not call the account verified-bad, do not re-OAuth, and do not delete it. Separately verify the account remains `isActive=true`, `testStatus=active`, with no error fields.

Never print or expose API keys, cookies, refresh tokens, or full request credentials in the report.
