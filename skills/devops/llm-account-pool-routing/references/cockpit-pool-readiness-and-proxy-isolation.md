# Cockpit pool readiness and proxy isolation

Use this gate whenever a user asks to build or verify a multi-account Codex/Cockpit pool.

## Live-state gate

External sources are candidate inventories only. A GPM workbook, supervisor state, OmniRoute SQLite row, refresh token, or profile ID does not prove that Cockpit imported the account. Verify the live Cockpit files/state:

- Count accounts in `codex_accounts.json`.
- Count accounts in the sidecar `manifest.json`.
- Require both counts to equal the requested pool size.
- Require every intended email to appear in the live account list.
- If counts or emails do not match, report `N/M live` and list missing accounts. Do not say the pool is complete.

## Proxy isolation gate

A shared API key is only a local ingress credential. It does not mean all accounts share one egress IP, and it does not prove that each account has a different egress IP. Keep the layers explicit:

`GPM profile → OAuth credential → Cockpit account → per-account proxy/node → shared Local API key → Hermes provider/fallback`

For every account, verify the Cockpit-side proxy binding/node and compare it to the intended farm mapping. Do not infer proxy assignment from an external workbook or from a canary request.

## Canary interpretation

A single HTTP 200 canary only proves that at least one available account can serve a request. It does not exercise the entire pool. After a canary, report exactly how many accounts are live and how many were actually tested. A pool can return `POOL_READY` while still containing only one account.

## Reporting rule

Use precise wording such as:

- `Cockpit live: 1/10 accounts; canary passed for 1 account.`
- `Candidate mapping: 10 GPM profiles found; 9 still not imported into Cockpit.`
- `Shared API key: yes; per-account egress isolation: verified/unverified.`

Never turn a candidate list into a DONE claim. This distinction prevents accidentally telling the user that ten accounts are isolated when Cockpit currently contains one account and one proxy binding.
