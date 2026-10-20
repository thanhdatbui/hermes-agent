---
name: order-tracking-automation
description: "Use for orders, mail codes, carrier scans, or dashboards."
version: 1.0.0
license: Proprietary
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [orders, tiktok-shop, outlook, hotmail, tracking, carrier-api, dashboard, cron]
    related_skills: [hotmail-outlook-automation, evidence-first-delivery, taadaa-farm-ops-rules]
---

# Order Tracking Automation

## Purpose

Use this class skill for order-management workflows where an order begins inside a shopping app/account, a mailbox may reveal the carrier tracking code, carrier systems provide route events, and a local dashboard presents canonical state.

The central design rule is a two-stage pipeline:

```text
Shop/app or mailbox -> discover tracking code + carrier
Carrier API/page -> monitor shipment scans and local-hub arrival
Dashboard/JSON/Excel -> display the same canonical order state
```

Do not describe mailbox polling as real-time shipment tracking. Mail is a discovery source for the dispatch message and tracking code; carrier tracking is the source for transit and hub events.

## Workflow

1. **Create one canonical order record.** Store order ID, recipient, destination, product, source account/device, image evidence, status, tracking code, carrier, last event, and timestamps. Keep JSON as the script source of truth; treat Excel as a presentation/export surface.
2. **Build a target-scoped mail reader.** Read only the target mailbox/profile and a bounded recent inbox slice. Parse subject/body for the target order or dispatch markers. Extract tracking code and carrier conservatively; reject ambiguous or code-free messages.
3. **Prefer an already-authenticated Outlook web session.** Resolve the GPM profile by exact mailbox plus machine/proxy identity when duplicates exist. Never select an arbitrary duplicate when the account/device binding matters.
4. **Keep Graph optional and explicit.** Use Graph only with a valid caller-supplied access token or separately managed refresh-token flow. Never infer token validity from mailbox address, password, or profile existence. Never print credentials, tokens, or complete mail bodies.
5. **Make mail sync one-shot and idempotent.** Provide `--once` and an offline parser self-test. Store dedup state keyed by order ID plus tracking code and, where useful, message identity. No new code means silent output; auth/session failure means a concise warning without secrets.
6. **Hand off to carrier tracking.** Once a code exists, query the carrier adapter. Normalize events to `{time, description, location}`. Detect destination hub/bưu cục using Vietnamese and normalized-ASCII keywords. Distinguish “arrived at hub” from “out for delivery”; do not claim pickup availability unless event semantics support it.
7. **Alert on the actionable milestone.** For local pickup, alert on a destination-hub scan with code, carrier, latest location, and time. Advise contacting the hub to hold the parcel; do not claim the script can prevent courier dispatch unless a hold request is confirmed.
8. **Integrate the dashboard only after the data path works.** Add an orders tab, `/api/orders` endpoint, and image route only after verifying the endpoint returns the canonical record. A rendered card proves UI integration, not live mail or carrier connectivity.
9. **Schedule at a practical cadence.** While waiting for a dispatch code, 15–30 minutes is appropriate for a time-sensitive pickup goal; 12 hours is too coarse. Use script-only/no-agent cron where supported. Keep the script one-shot; do not create an invisible infinite loop.
10. **Verify before reporting DONE.** Run offline parser self-test, one live read when session/credentials are available, inspect JSON state, read the dashboard endpoint back, and report separately: mail session, tracking code, carrier tracking, dashboard, and schedule. Cron status `ok` alone is not proof the script read mail or updated an order.

## Dashboard image integrity

When an order dashboard displays screenshots or product photos, preserve the source artifact instead of treating a single thumbnail as the complete order evidence:

1. Store image assets as an explicit list with roles such as `order_confirmation`, `product`, `shipping_address`, and `tracking_event`; keep the original files immutable.
2. Render portrait screenshots with their native aspect ratio (`height:auto` / `object-fit:contain`), not a forced 4:3 crop with `object-fit:cover`. A card thumbnail must wrap in an anchor link (`target="_blank"`, `cursor:zoom-in`) directly opening the raw uncropped image endpoint (e.g. `/orders/images/<filename>`) on click.
3. Verify the image route and the actual browser rendering separately. A valid JSON `image_path` proves storage, not that the UI shows the full image. When the user asks to view the raw image on web, navigate to `/orders/images/<filename>` and verify via vision that all critical segments (status, recipient, address, item details) are intact without cut borders.
4. Hot-reload dashboard behind watchdog: when modifying dashboard code (e.g. `tiktok_dashboard.py`), terminating the running process allows the supervisor watchdog (`tiktok_dashboard_watchdog.ps1`) to respawn a clean instance with the updated code within seconds.
5. Treat a card that shows only order metadata or a cropped screenshot as incomplete evidence; report the missing image role explicitly rather than claiming the order gallery is complete.
6. Keep the canonical order record, image manifest, and dashboard response aligned. If the schema supports only one `image_path`, add a backward-compatible `images` list rather than silently overwriting the existing asset.

Session detail and reproduction notes: `references/order-card-image-integrity.md`.

## Safety and privacy

- Do not put passwords, refresh tokens, access tokens, cookies, or full email bodies in logs, dashboard payloads, cron prompts, or Telegram messages.
- Limit customer phone/address exposure to the intended dashboard and actionable alert.
- Use device locks before real-device interaction. Prefer web-session reading when it avoids touching a live farm device.
- Treat screenshots and worker self-reports as evidence to verify, not permission to invent missing tracking data.

## Reporting format

Report facts by layer, briefly:

- `Mail session:` verified / blocked / not tested, with evidence.
- `Tracking code:` present / absent.
- `Carrier tracking:` last verified event or unavailable.
- `Dashboard:` endpoint/card verified or not verified.
- `Schedule:` exact cadence and job ID only when actually created and read back.

Do not say “real-time” when polling. State the interval and likely detection delay.

## References

- `references/order-mail-to-carrier-handoff.md` — mailbox discovery, profile disambiguation, dedup state, carrier handoff, and evidence labels.
