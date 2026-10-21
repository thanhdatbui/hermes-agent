# OmniRoute OAuth preflight and single-profile execution notes

## Verified session lessons

1. **Check OmniRoute inventory before starting OAuth.** Query the provider inventory used by the canonical script (`GET /api/providers`) and compare the normalized target email. A profile may be reported as `unadded` by a stale/local mapping while OmniRoute already contains the email; treat the live OmniRoute inventory as the authority for whether this is a new add or a re-auth/repair.
2. **Bind one exact GPM profile.** Resolve the unique profile by exact email/profile ID, preserve its assigned proxy, and start it through `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?skip_proxy_check=true`. Use the returned `remote_debugging_address` with `connect_over_cdp`; do not launch a second persistent context over the same profile.
3. **Use the canonical single-account script only.** The legacy relogin/batch helper may not expose the same single-profile CLI contract; invoking it with unsupported flags can fall through into a large batch. Before execution, run its `--help` and confirm the exact account/profile selector. If it cannot prove a single-target mode, do not use it for a one-account OAuth task.
4. **Explicit authorization changes the decision gate, not the evidence gate.** If the operator explicitly authorizes OAuth, the agent may proceed even when the profile has a prior purpose label, but must still verify the exact target account, proxy/profile binding, Google consent state, callback/exchange response, and post-action OmniRoute inventory. A started process or browser URL is not OAuth success.
5. **Stop on human-verification blockers.** CAPTCHA, Google phone/recovery challenge, or an account chooser that cannot be resolved from the already-authenticated target is a bounded manual-needed result. Do not enter secrets or invent OTPs.

## Evidence contract

Record the exact profile ID, GPM start response, CDP endpoint (do not publish secrets), OAuth script command, OmniRoute preflight result, callback/exchange result, and post-action provider record. Report `ALREADY_PRESENT`, `REAUTH_REQUIRED`, `ADDED`, or `BLOCKED` explicitly; never collapse these into a generic success.
