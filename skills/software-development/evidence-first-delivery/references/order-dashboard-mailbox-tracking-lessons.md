# Order dashboard + mailbox tracking lessons

## Validated patterns
- An order dashboard can expose a JSON endpoint, an image route, and a rendered order card; verify all three independently.
- A TikTok Shop order may expose the carrier/tracking code through shipment email or the TikTok order page. Until a code exists, carrier APIs cannot track the parcel.
- Mailbox access states must be evidence-based: `LIVE_READ_OK`, `TOKEN_INVALID`, `AUTH_REQUIRED`, `TIMEOUT`, or `NOT_PROBED`. Do not collapse these into “password changed”.
- OTP readers and shipment-mail readers are different consumers. Shipment polling needs sender/subject/body parsing, message-id deduplication, tracking-code extraction, and order-ledger update.
- A 12-hour poll is unsuitable when the user wants to reach a local hub before a courier departs; use a bounded 15–30 minute cadence while waiting for the code, then carrier polling after code discovery.

## Reporting checklist
1. State what was implemented.
2. State what was live-tested and include status/result class.
3. State what is not configured.
4. For UI claims, attach the freshly inspected screenshot.
5. Never print credentials, access tokens, refresh tokens, or full private message bodies.

## Common pitfall
Do not report “Hotmail is connected” because a workbook contains an email, a script exists, or a cron with a similar name exists. The dedicated order-mail reader and its schedule must be verified separately.
