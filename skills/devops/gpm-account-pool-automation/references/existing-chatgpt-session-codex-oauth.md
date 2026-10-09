# Existing ChatGPT Session → Codex OAuth

## Trigger
Use when attaching Codex/OAuth to a ChatGPT account already held in a GPM profile.

## Hard gates

1. Inventory GPM profiles plus OmniRoute providers before OAuth. Prefer a live `chatgpt-web` provider and a fresh CDP screenshot showing the ChatGPT account/avatar/conversation UI.
2. If the profile lands on `auth.openai.com/log-in`, shows `Log in`, or shows `Sign up for free`, classify it as `SESSION_MISSING` and exclude it. Do not log in again, register, guess a password, or use SSO to repair it.
3. Google SSO is forbidden in this lane: never click `Continue with Google` or open a Google chooser. Direct Email+OTP ChatGPT registration is a separate lane and must not be mixed into Codex OAuth.
4. Only after the existing session is visually confirmed may Codex OAuth start. A native account chooser/consent is acceptable only for selecting the already-authenticated ChatGPT identity.
5. Do not buy a 5SIM number until the live UI is confirmed as the OpenAI/Codex phone-verification page. If OAuth completes without `add-phone`, finish without buying a number.
6. If phone verification is required, use at most two attempts, cancel immediately on rejection/timeout, and capture pre-submit, post-submit, OTP, and final screenshots. Success requires both an OmniRoute connection ID and UI evidence.

## Evidence states

- `REGISTERED_NEW`: direct-registration log plus success screenshot.
- `PREEXISTING_SESSION`: fresh live ChatGPT UI before OAuth.
- `DATA_ONLY_UNVERIFIED`: Excel/log/provider marker without fresh live proof.
- `SESSION_MISSING`: OAuth lands at login/guest UI.
- `BANNED/INACTIVE`: provider is banned or inactive.

## Proven pattern

A valid existing-session candidate was found by reconciling GPM inventory, `chatgpt-web` provider state, and a fresh CDP screenshot. Codex OAuth then completed through the existing identity and created an active OmniRoute Codex connection without buying a phone number. This is the preferred path: verify session first; phone verification is conditional, not automatic.
