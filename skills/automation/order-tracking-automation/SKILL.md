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

The central design rule is a multi-channel discovery and tracking pipeline:

```text
[Discovery Channel A (Passive)] Webmail (Outlook GPM) -> parse dispatch email
[Discovery Channel B (Active)]   TikTok App (Farm Device) -> in-app order detail via atx-agent JSONRPC
                                     │ (tracking code + carrier)
                                     ▼
Carrier API/page (SPX/J&T/Ninja) -> monitor shipment scans and local-hub arrival
Dashboard/JSON/Excel             -> display the same canonical order state
```

Do not rely solely on mailbox polling as tracking code discovery. TikTok Shop and sellers frequently omit or delay tracking emails until after delivery; in-app order inspection on the farm device is the authoritative zero-delay source of truth. Carrier tracking remains the sole source for transit and hub events.

## Workflow

1. **Create one canonical order record.** Store order ID, recipient, destination, product, source account/device, image evidence, status, tracking code, carrier, last event, and timestamps. Keep JSON as the script source of truth; treat Excel as a presentation/export surface.
2. **Build a target-scoped mail reader.** Read only the target mailbox/profile and a bounded recent inbox slice. Parse subject/body for the target order or dispatch markers. Extract tracking code and carrier conservatively; reject ambiguous or code-free messages.
3. **Dual-path discovery: Mailbox vs In-App TikTok Shop tracking (Dual-engine: WinRT OCR PRIMARY, XML fallback).**
   - *Passive Path (Mailbox):* Read GPM Webmail / Outlook session. Zero device disruption, ideal for frequent background cron.
   - *Active Path (In-App Ground Truth):* When mailbox polling returns no tracking code (as TikTok Shop frequently omits dispatch emails or delays them until delivery), inspect the order directly inside the TikTok app on the farm device. Run strictly under `with_device_lock.py --machine <N>`, verify that the active TikTok account matches the order's slot/row handle via Profile/Switcher, navigate to My Orders, extract the carrier name and tracking code, update canonical records, force-stop TikTok, and release the lock immediately.
   - **WinRT OCR MUST BE PRIMARY (User Invariant):** Do not prioritize UI XML hierarchy over OCR for in-app order details. Shopping order screens frequently render via embedded WebViews, Flutter, or custom layouts where Android accessibility nodes have empty `text` or `content-desc`. Screen capture combined with Windows Native OCR (`Windows.Media.Ocr.OcrEngine` with language tag `vi-VN` / `en-US` transliteration) operates directly on rendered pixels, reliably capturing tracking codes (`SPXVN...`, `JNT...`, `8-30` alphanumerics) and carriers (`SPX Express`, `J&T`, `Ninja Van`, `Viettel Post`, `GHTK`).
   - **Banned Direct XML Dumps (Hard Gate Enforcement):** In-app TikTok Shop and WebViews strictly ban direct XML dumps (`dumpWindowHierarchy`, `uiautomator dump`, port `7912`). Enforced mechanically via `tools/ui_policy_check.py` and `done_gate.py`. Extraction must go through `automation_core.ui_extract` (WinRT OCR Primary with fail-closed WebView rules).
   - **Screen Sleep / Dozing Trap on S7 during Order Inspection:** Farm devices in night shift/idle enter `mWakefulness=Dozing`, producing all-black screencaps `(0,0,0,255)` that return 0 OCR boxes. Before OCR, keep screen awake via `settings put system screen_off_timeout 1800000` (30m) and `settings put global stay_on_while_plugged_in 3`, and inject `KEYCODE_WAKEUP` + unlock `82` whenever an all-black/empty OCR capture occurs.
   - **Word-by-Word Levenshtein OCR Matching:** WinRT OCR with English language packs distorts Vietnamese diacritics (`Hồ sơ` -> `Hö sd`, `Cửa hàng` -> `CÜa häng`, `Chuyển đổi tài khoản` -> `Chuydn ddi täi khoån`, `Đơn hàng của bạn` -> `Ddn häng cia bqn`). Plain exact match fails, while generic Levenshtein <= 3 mistakenly matches `Đơn hàng của bạn` (profile entry button) with `Đơn hàng của tôi` (orders list title). Solution: use word-by-word Levenshtein distance <= 1 (`all(levenshtein_distance(wf, ww) <= 1 for wf, ww in zip(words_f, words_w))`) which perfectly distinguishes entry buttons from list titles.
   - **Account Switcher & Order Entry Flow:**
     * Tapping username text (`@username`) merely copies to clipboard. To open switcher, tap display name or dropdown area `(w/2, h * 0.08)`, or long-press Profile tab at bottom right.
     * When the switcher bottom sheet opens, detect target handle directly (`_find_handle_center`) and tap it.
     * On the target profile, tap "Đơn hàng của bạn" or "Cửa hàng" tab (`w ≈ 320, y ≈ 1885`) to navigate to TikTok Shop orders.
   - **Keyguard / Scrim Silent Touch Absorption (`Bouncer` / `ContainerKeyguardScrim`):**
     * On Samsung/Android farm devices, `dumpsys window windows` can reveal `Window{... Bouncer}` or `Window{... ContainerKeyguardScrim}`. Even though screen capture displays the underlying app, touch events (`input tap`) are silently absorbed by the lockscreen scrim (ADB exits 0 with zero effect).
     * Fix: Always issue `wm dismiss-keyguard` and `input keyevent 82` before UI interaction. Avoid using blind `input swipe` to unlock when the app might already be running, as the swipe will scroll the underlying page down.
   - **Foreground Focus vs Background Process (`pidof` Trap):**
     * Never use `pidof <package>` to decide whether an app is visible. When waking from sleep or background cron, the process may exist in memory while the foreground window (`mCurrentFocus`) is Samsung Launcher (`com.sec.android.app.launcher`).
     * Fix: Check `dumpsys window windows | grep mCurrentFocus` or proactively issue `am start -n <package>/<splash_activity>` whenever the package is not the active focus.
   - **Scrolled Profile Navigation Recovery:**
     * When a profile page is scrolled down, header handles (`@username`) and shortcut buttons ("Đơn hàng của bạn") scroll off-screen.
     * Fix: Detect profile presence via metrics (`follower`, `thích`, `bài đăng`), and if header shortcuts are missing, swipe down (`swipe 540 400 540 1600 300`) to scroll back up and reveal the shortcuts.
   - **Order List vs Detail Screen Tracking Extraction:**
     * The order list card shows high-level status ("Đang trung chuyển"), item, and price. Tapping the tracking timeline banner or the product item navigates into the detailed Delivery Status screen to uncover the full carrier name and tracking number.
   - **Physical vs ADB Triage:** When a farm device goes missing during or before in-app order inspection, inspect `Get-PnpDevice` (`Present: True` vs `False`). If Windows PnP reports `Present: False` AND Wi-Fi drops concurrently at the same timestamp, classify as hardware power loss or physical cable disconnect rather than a soft ADB transport hang.
4. **Prefer an already-authenticated Outlook web session.** Resolve the GPM profile by exact mailbox plus machine/proxy identity when duplicates exist. Never select an arbitrary duplicate when the account/device binding matters.
4. **Verify token API in canonical inventory; keep Graph optional.** When checking if an account has an API token or changed password, do not speculate or give rambling explanations: inspect `gmail_clean_v2.xlsx` directly (Sheet `Gmail Accounts`). Col 9 (`token`) and Col 10 (`client_id`) show whether an OAuth token was provisioned (if `None`, definitively report NO token API and fall back directly to GPM web session). Compare Col 3 (`pass mail`) with `taikhoan_dat_v2_updated .xlsx` Col 7 (`PASS MAIL`) to verify password consistency. Never print credentials, tokens, or complete mail bodies.
5. **Supplier order history & ShopClone7/BoxTaiKhoan audit discipline.** When tracing account origins on MMO shops (e.g. `boxtaikhoan.com` / ShopClone7):
   - **Chống phán đoán xóa đơn vội vã (Anti-Premature Deletion Trap):** Các câu cảnh báo trên UI như *"Lịch sử đơn hàng chỉ lưu trong 3 ngày... có thể bị xóa"* chỉ là thông báo khuyến cáo tranh chấp của web, KHÔNG PHẢI bằng chứng database đã bị xóa. Tuyệt đối không được vội vã kết luận đơn cũ đã bị xóa chỉ vì đọc dòng chữ này. Bắt buộc kiểm tra bảng đơn hàng thực tế (`/product-orders`), lùi phân trang (`?page=N`), hoặc kiểm tra nhật ký tài khoản (`/client/logs`).
   - **Bẫy mã lỗi HTTP 404 của ShopClone7:** Endpoint như `api/order.php` trả về HTTP 404 (kèm trang HTML 404) khi mã đơn `order` truyền vào không tồn tại, không có nghĩa là file `api/order.php` không tồn tại trên máy chủ.
   - **Nhận diện hết hạn phiên trên trình duyệt Host:** Các trang quản lý đơn yêu cầu đăng nhập. Khi điều hướng mà bị chuyển hướng về `/client/login`, phiên đăng nhập đã hết hạn; không cố gửi click mù vào iframe Google OAuth mà báo người dùng xác thực lại trên tab Chrome đang mở.
6. **Make mail sync one-shot and idempotent.** Provide `--once` and an offline parser self-test. Store dedup state keyed by order ID plus tracking code and, where useful, message identity. No new code means silent output; auth/session failure means a concise warning without secrets.
7. **Hand off to carrier tracking.** Once a code exists, query the carrier adapter. Normalize events to `{time, description, location}`.
   - **Direct Carrier Web Tracking URLs:** For instant user lookup, direct links are more resilient than deprecated API endpoints (e.g., J&T Express API `/api/tracker` returns 404, whereas public web tracker `https://jtexpress.vn/vi/tracking?type=track&billcode={code}` is canonical). SPX: `https://spx.vn/track?{code}`.
   - **Sorting Hub vs Delivery Hub (Bưu Cục Phát):** Major carriers (J&T, SPX) route through provincial/city sorting centers (e.g. Trung tâm phân loại Liên Chiểu in Da Nang) before dispatching to local district delivery post offices (bưu cục phát như Thanh Khê, Tam Thuận). An arrival scan at a provincial sorting center means the parcel is in-city, typically transferring to local delivery hubs on the next morning cycle (e.g., 06:00 AM scan) for same-day delivery.
   - **COD vs Cart Total Reconciliation:** In-app tracking displays the actual payable COD amount (`Hãy chuẩn bị sẵn <amount>đ tiền mặt`) which often differs from the initial cart item total due to applied platform vouchers/shipping discounts. Always extract and record `cod_amount` alongside `total` to ensure accurate delivery cash preparation. Detect destination hub/bưu cục using Vietnamese and normalized-ASCII keywords. Distinguish “arrived at hub” from “out for delivery”; do not claim pickup availability unless event semantics support it.
8. **Alert on the actionable milestone.** For local pickup, alert on a destination-hub scan with code, carrier, latest location, and time. Advise contacting the hub to hold the parcel; do not claim the script can prevent courier dispatch unless a hold request is confirmed.
9. **Integrate the dashboard only after the data path works.** Add an orders tab, `/api/orders` endpoint, and image route only after verifying the endpoint returns the canonical record. A rendered card proves UI integration, not live mail or carrier connectivity.
10. **Schedule at a practical cadence.** While waiting for a dispatch code, 15–30 minutes is appropriate for a time-sensitive pickup goal; 12 hours is too coarse. Use script-only/no-agent cron where supported. Keep the script one-shot; do not create an invisible infinite loop.
11. **Verify before reporting DONE.** Run offline parser self-test, one live read when session/credentials are available, inspect JSON state, read the dashboard endpoint back, and report separately: mail session, tracking code, carrier tracking, dashboard, and schedule. Cron status `ok` alone is not proof the script read mail or updated an order.

## Dashboard image integrity

When an order dashboard displays screenshots or product photos, preserve the source artifact instead of treating a single thumbnail as the complete order evidence:

1. Store image assets as an explicit list with roles such as `order_confirmation`, `product`, `shipping_address`, and `tracking_event`; keep the original files immutable.
2. Render portrait screenshots with their native aspect ratio (`height:auto` / `object-fit:contain`), not a forced 4:3 crop with `object-fit:cover`. A card thumbnail must wrap in an anchor link (`target="_blank"`, `cursor:zoom-in`) directly opening the raw uncropped image endpoint (e.g. `/orders/images/<filename>`) on click.
3. Verify the image route and the actual browser rendering separately. A valid JSON `image_path` proves storage, not that the UI shows the full image. When the user asks to view the raw image on web, navigate to `/orders/images/<filename>` and verify via vision that all critical segments (status, recipient, address, item details) are intact without cut borders.
4. Hot-reload dashboard behind watchdog: when modifying dashboard code (e.g. `tiktok_dashboard.py`), terminating the running process allows the supervisor watchdog (`tiktok_dashboard_watchdog.ps1`) to respawn a clean instance with the updated code within seconds. Be aware of watchdog initial sleep latency (up to 60s) after host reboots before treating `WinError 10061` as service failure.
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
- `references/order-card-image-integrity.md` — preserve raw image aspect ratio and zoom links on order dashboards.
- `references/shopclone7-boxtaikhoan-order-audit.md` — ShopClone7/BoxTaiKhoan order retention reality vs 3-day UI warning, API 404 behavior, and host Chrome login session.
- `references/tiktok-in-app-order-tracking.md` — In-app order inspection protocol, device locking, account verification, and carrier handoff.
