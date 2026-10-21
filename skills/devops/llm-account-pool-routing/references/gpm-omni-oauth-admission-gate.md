# GPM → OmniRoute OAuth admission gate

## Trigger
Use before re-authenticating a Google account into OmniRoute/Antigravity when the same GPM inventory may also contain Codex-only or otherwise reserved profiles.

## Verified workflow

1. **Enumerate the complete GPM inventory.** Do not trust a requested `limit`; inspect the response pagination (`total_page`, `page`, `page_size`) and iterate every page. Resolve by exact normalized email with an email-boundary match and require exactly one result.
2. **Read live profile metadata before opening it.** Record profile ID, display name, `raw_proxy`, profile path, and `note`. A note such as `CODEX_SESSION_ONLY` or `CODEX_SESSION_ONLY__DO_NOT_OAUTH_ANTIGRAVITY` is an ownership lock, not a suggestion.
3. **Fail closed on reserved profiles.** Never run Antigravity/Omni OAuth on a Codex-only GPM profile, never overwrite its session, and never reuse its proxy assignment for a new OAuth connection. Find or create a separately designated OAuth profile with explicit proxy ownership, or escalate the business decision.
4. **Preserve requested ordering.** If the operator says “Omni OAuth first, AGY CLI second,” finish Omni OAuth and verify it before provisioning/enabling the AGY CLI sandbox.
5. **Require live completion evidence.** For Omni OAuth, verify a fresh connection ID, live subscription/tier response, 1:1 proxy assignment, and intended combo membership. Existing DB rows, stale `g1-pro-tier` labels, or a script exit code alone are not proof.

## Incident lesson

A profile can exist in GPM and have the target email while still being unsuitable for Omni OAuth because it is reserved for another provider. In that case, “profile found” is not equivalent to “safe OAuth target.” Report the exact profile metadata and the ownership blocker instead of silently reusing it.

## Safety notes

- Do not infer a missing account from page 1 of a paginated API.
- Do not repurpose a Codex session merely because the account has a valid proxy.
- Keep OmniRoute onboarding and later AGY CLI sandboxing as separate phases with separate verification receipts.
