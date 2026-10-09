# Bounded Codex OAuth Live-Run Evidence

Use for GPM Login v3 + Playwright/CDP + OmniRoute :20129 + 5SIM OpenAI phone verification.

## Required sequence

1. Query live GPM profiles and match both the exact profile ID and target email. Do not trust a runner's old default account.
2. Read the complete current runner before broad edits. If a file read was paginated/truncated, re-read the relevant full file before patching.
3. Require explicit `--profile-id` and `--email` (or an explicit runner object). Enforce the attempt budget in code. Use the requested order, e.g. Vietnam/virtual34 first and Colombia/virtual34 only as fallback; never rotate a generic pool or loop indefinitely.
4. Start the OmniRoute callback server before navigation. Forward a localhost callback at most once per run to reduce CDP/callback races. Poll on a bounded deadline.
5. Before buying any number, require fresh live UI evidence: `auth.openai.com`, the phone-verification route, a telephone input, and verification-related DOM text. Persist a screenshot before purchase and again before submit.
6. Persist a fresh after-submit screenshot for each attempt. On OpenAI rejection or OTP timeout, cancel/refund immediately and do not call 5SIM `finish`. Continue only to the explicitly allowed fallback.
7. Enter OTP and click Authorize only after fresh UI evidence confirms the expected state. Persist after-OTP and final OAuth screenshots.
8. Poll OmniRoute and accept success only when the response is successful and contains a concrete connection ID. `pending`, HTTP 200, or a free-text success message is not proof.
9. Always stop the exact GPM profile in `finally`, including early returns and exceptions. Preserve raw stdout/stderr, order actions, poll payloads, and screenshot paths.

## Closeout gate

Do not report DONE unless the live run produced both inspectable UI screenshot paths and an OmniRoute connection ID. `py_compile` is syntax evidence only, not live E2E evidence.

## Known failure modes

- Hardcoded `voha`/older target can silently operate on the wrong aged account.
- A generic live-pool sorter violates a two-attempt country/operator contract.
- Buying before a DOM gate risks charging a number while the browser is still on OAuth/login/about-you.
- Treating `poll-callback: {pending: true}` as success creates false connections.
- Calling `finish` before connection-id confirmation prevents safe refund on incomplete OAuth.
