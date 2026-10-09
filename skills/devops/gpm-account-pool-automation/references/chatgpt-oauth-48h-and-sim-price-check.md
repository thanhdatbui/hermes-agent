# ChatGPT OAuth 48-hour eligibility and SIM-price check

## Account-state classification

- `ALREADY_LOGGED_IN` means the GPM profile already had a ChatGPT session; it does not prove a new registration in the current run.
- A run that filled the ChatGPT password and fetched/submitted an OTP is a `NEW_REG_ATTEMPT`; do not infer success or account age from a result filename alone.
- Keep provider errors separate from account bans. HTTP 403 `insufficient_quota` is evidence of provider/quota/credential rejection, not an account ban unless the live account UI independently proves a ban.

## OAuth eligibility matrix

Before Codex OAuth or phone verification, reconcile the exact GPM profile with live OmniRoute provider metadata:

1. ChatGPT Web connection exists and is active.
2. The email has no existing Codex connection, or the operator explicitly wants a reauthorization.
3. The relevant ChatGPT Web `createdAt` is at least 48 hours old.
4. Exclude `banned`, inactive, duplicate, or ambiguous connections.
5. Report the age as **provider-session age**, not guaranteed ChatGPT account-creation age.
6. Use one eligible canary first; only expand after OAuth is verified.

## Paid SIM comparison gate

Before spending balance or purchasing a number:

- Inspect at least two live providers in the user-authorized browser/CDP session.
- Record exact provider, service/product, country, visible price, stock/availability, login/session state, and timestamp.
- Treat public `from $X` prices as leads only; they are not the checkout price for OpenAI/Codex.
- If a provider is logged out, expired, or only exposes a dashboard after login, label exact pricing `UNVERIFIED`.
- Stop at the comparison/verification page. Do not buy, reserve, enter a phone number, or submit OTP without explicit authorization.

Observed examples from one session (not durable pricing): 5SIM public page showed OpenAI/ChatGPT country "from" prices; ViOTP showed a dashboard balance and historical Gmail pricing but not a verified Codex/OpenAI price; SMS-Activate reported that the service had closed. These are evidence examples, not current price claims.
