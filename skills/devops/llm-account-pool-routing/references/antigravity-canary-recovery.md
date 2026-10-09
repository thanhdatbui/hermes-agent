# Antigravity Canary Recovery: Profile Isolation and Evidence Gates

Use this procedure when an Antigravity/Gemini account returns repeated 403/VALIDATION_REQUIRED or has a disputed project assignment.

## Hard boundaries

- Never recover multiple accounts through one shared browser profile, cookie jar, local storage, or unverified device context. A shared app binary is not the same as a shared session, but session/profile/proxy isolation must be proven.
- Never guess a GPM profile from a similar display name. Resolve the exact account email to a profile ID, then verify the displayed account and proxy before any UI/OAuth action.
- Never delete credentials, overwrite tokens, blank `projectId`, or re-add the account to production traffic before evidence is captured.
- Never substitute `aicode-consumers` for a missing user-owned project.

## Canary sequence

1. Read-only baseline: connection row, sanitized provider metadata, recent real model errors, combo membership, and active/disabled state.
2. Isolate the one canary from production combos. Preserve the DB row and credentials.
3. Open only the exact dedicated GPM profile. Capture/verify profile ID, displayed Gmail, proxy, and current page. If the profile cannot be found, stop BLOCKED and request the exact profile ID/name.
4. Perform at most one bounded recovery/onboarding action. Stop on phone checkpoint, security challenge, CAPTCHA, or ambiguous account state; do not loop.
5. Re-read the entitlement and project state. Classify explicitly:
   - real user-owned project replacing `aicode-consumers`;
   - still `aicode-consumers`;
   - `422 missing projectId` / `gcp_project_required`;
   - project changed but model still returns `403`.
6. Only for the first case, issue one short real model request through the connection ID. A single HTTP 200 is not enough to restore farm traffic; require a bounded representative check and no entitlement error.
7. Keep the account isolated after any failed canary and record the exact evidence. Do not proceed to the remaining accounts until the canary is understood.

## Failure interpretation

- Semaphore timeout is a local capacity symptom, not proof that Google quota is dead; fix fail-fast spillover separately.
- Repeated upstream 403 across multiple models is an entitlement/project/policy signal and must not be “fixed” by retrying or changing local labels.
- OAuth success alone proves token exchange, not Antigravity entitlement or project provisioning.

## Operator reporting

Report the exact profile lookup result, account/project before and after, model status, and next gate. If the exact profile is unavailable, say `BLOCKED` and include the lookup evidence; do not open a near-match.
