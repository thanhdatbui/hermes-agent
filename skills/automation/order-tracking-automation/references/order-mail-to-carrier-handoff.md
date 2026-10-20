# Order Mail → Carrier Handoff

## Validated pattern

A TikTok Shop order may be represented in local JSON while it is still `Đã đặt hàng` and has no `tracking_code`. Do not query carrier APIs until a dispatch message or app read yields a code.

### Mail discovery

- Target one mailbox and one order ID; do not scan the whole farm mailbox pool.
- Prefer an authenticated Outlook web session in the matching GPM profile.
- When a mailbox has duplicate GPM profiles, match the profile name to the machine/proxy identity (example: `38 - <mailbox> - 20038`).
- Parse bounded recent rows and open only candidate TikTok/order messages.
- Store dedup state by `order_id|tracking_code`; no new code should produce empty stdout.
- Session/auth errors should identify the recovery action but never include password, token, cookie, or full message content.

### Graph API

Graph is optional, not assumed. A mailbox address, password, or existing GPM profile does not prove a usable Graph token. Accept a caller-supplied token/refresh flow from a secret manager or environment and report `UNVERIFIED` when no live token evidence exists.

### Carrier handoff

After a code is found, normalize carrier events to:

```json
{"time": "...", "description": "...", "location": "..."}
```

Detect destination hub/bưu cục using both Vietnamese and accent-stripped terms such as `Đà Nẵng`/`da nang`, `Thanh Khê`/`thanh khe`, `bưu cục`, `nhập kho`, `arrived at hub`. Keep `out for delivery` separate from hub arrival. A hub scan is an actionable signal to call the carrier and request hold; it is not proof that pickup is already authorized.

### Scheduler and evidence

Use a one-shot `--once` script under a script-only/no-agent cron wrapper. For urgent local pickup, 15–30 minute polling is appropriate; 12 hours is not. Verify each layer independently:

1. offline parser self-test;
2. live mailbox/session result;
3. JSON state readback;
4. carrier lookup after a real code exists;
5. dashboard `/api/orders` readback and visual card check;
6. cron record plus a real output/artifact, not cron `ok` alone.

In reports, separate `Mail session`, `Tracking code`, `Carrier tracking`, `Dashboard`, and `Schedule`. Never call polling “real-time”; state the interval and expected delay.
