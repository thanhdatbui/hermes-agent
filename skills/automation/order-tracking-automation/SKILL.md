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
     * **J&T Express 12-Digit Numeric Billcode Extraction Pitfall:** On the TikTok Shop "Theo dõi kiện hàng" (Tracking Details) screen for J&T Express, the billcode is often displayed as a standalone 12-digit number (e.g. `862643546861`) without the prefix `"Mã vận đơn:"` or `"JNT"`. Generic regexes expecting `TRACKING_LABEL` miss this completely. Always check for J&T 12-digit numeric billcodes matching `\b(8[4-9]\d{10})\b` when carrier is J&T or when no prefixed tracking code is found.
     * **Profile Handle Ambiguity vs Switcher Trap:** On TikTok user profiles, the username handle (e.g. `@tooanh2604`) is displayed directly under the avatar. If the navigation loop checks `_find_handle_center(...)` to detect whether the switcher is open without verifying an explicit switcher title (`Chuyển đổi tài khoản`, `Thêm tài khoản`, `Switch account`), it mistakes the profile screen for the switcher sheet and endlessly taps on the profile username instead of tapping "Đơn hàng của bạn". Always enforce an explicit switcher sheet marker before treating handle coordinates as a switcher selection, and prioritize tapping `ORDER_ENTRY_LABELS` once on the target profile.
     * **Double Device-Lock Deadlock Trap:** When an automation script (like `tiktok_app_order_sync.py`) already wraps internal ADB commands in `operator_device_lock(serial=...)`, do NOT redundantly wrap the outer execution in `with_device_lock.py --machine <N>`. The child process will deadlock or timeout waiting for the lock held by the parent process.
   - **Physical vs ADB Triage:** When a farm device goes missing during or before in-app order inspection, inspect `Get-PnpDevice` (`Present: True` vs `False`). If Windows PnP reports `Present: False` AND Wi-Fi drops concurrently at the same timestamp, classify as hardware power loss or physical cable disconnect rather than a soft ADB transport hang.
4. **Prefer an already-authenticated Outlook web session.** Resolve the GPM profile by exact mailbox plus machine/proxy identity when duplicates exist. Never select an arbitrary duplicate when the account/device binding matters.
4. **Verify token API in canonical inventory; keep Graph optional.** When checking if an account has an API token or changed password, do not speculate or give rambling explanations: inspect `gmail_clean_v2.xlsx` directly (Sheet `Gmail Accounts`). Col 9 (`token`) and Col 10 (`client_id`) show whether an OAuth token was provisioned (if `None`, definitively report NO token API and fall back directly to GPM web session). Compare Col 3 (`pass mail`) with `taikhoan_dat_v2_updated .xlsx` Col 7 (`PASS MAIL`) to verify password consistency. Never print credentials, tokens, or complete mail bodies.
5. **Supplier order history & ShopClone7/BoxTaiKhoan audit discipline.** When tracing account origins on MMO shops (e.g. `boxtaikhoan.com` / ShopClone7):
   - **Chống phán đoán xóa đơn vội vã (Anti-Premature Deletion Trap):** Các câu cảnh báo trên UI như *"Lịch sử đơn hàng chỉ lưu trong 3 ngày... có thể bị xóa"* chỉ là thông báo khuyến cáo tranh chấp của web, KHÔNG PHẢI bằng chứng database đã bị xóa. Tuyệt đối không được vội vã kết luận đơn cũ đã bị xóa chỉ vì đọc dòng chữ này. Bắt buộc kiểm tra bảng đơn hàng thực tế (`/product-orders`), lùi phân trang (`?page=N`), hoặc kiểm tra nhật ký tài khoản (`/client/logs`).
   - **Bẫy mã lỗi HTTP 404 của ShopClone7:** Endpoint như `api/order.php` trả về HTTP 404 (kèm trang HTML 404) khi mã đơn `order` truyền vào không tồn tại, không có nghĩa là file `api/order.php` không tồn tại trên máy chủ.
   - **Nhận diện hết hạn phiên trên trình duyệt Host:** Các trang quản lý đơn yêu cầu đăng nhập. Khi điều hướng mà bị chuyển hướng về `/client/login`, phiên đăng nhập đã hết hạn; không cố gửi click mù vào iframe Google OAuth mà báo người dùng xác thực lại trên tab Chrome đang mở.
6. **Make mail sync one-shot and idempotent.** Provide `--once` and an offline parser self-test. Store dedup state keyed by order ID plus tracking code and, where useful, message identity. No new code means silent output; auth/session failure means a concise warning without secrets.
7. **Hand off to carrier tracking.** Once a code exists, query the carrier adapter. Normalize events to `{time, description, location}`.
   - **Direct Carrier Web Tracking URLs & Privacy Gates:** For instant user lookup, direct links are more resilient than deprecated API endpoints (e.g., J&T Express API `/api/tracker` returns 404, whereas public web tracker `https://jtexpress.vn/vi/tracking?type=track&billcode={code}&cellphone={phone_last4}` is canonical). J&T requires the recipient's last 4 phone digits (`cellphone`); without this parameter, the web server hides the event timeline behind an input modal. SPX: `https://spx.vn/track?{code}`.
   - **Sorting Hub vs Delivery Hub (Bưu Cục Phát) & Inter-Hub Transit Pitfall:** Major carriers (J&T, SPX) route through provincial/city sorting centers (e.g. Trung tâm phân loại / TTKT Liên Chiểu in Da Nang) before dispatching to local district delivery post offices (bưu cục phát như Thanh Khê, Tam Thuận). An arrival scan at a provincial sorting center means the parcel is in-city, typically transferring to local delivery hubs on the next morning cycle (e.g., 06:00 AM scan) for same-day delivery. Retail self-pickup at an automated sorting center (SOC/TTKT) is strictly impossible; pickup must target the local delivery hub.
     * **Inter-Hub Dispatch Semantic Pitfall:** Event strings matching `Bưu cục【...】đang chuyển hàng đến【...】` denote inter-facility transport (xe tải đang lăn bánh), NOT arrival at destination hub. A blind substring match on `bưu cục` or hub names triggers false alarms (and sirens) while the parcel is still on the road. Arrival at the destination hub requires an arrival verb (`Hàng đã được chuyển đến【Bưu cục...】` / `Đã đến bưu cục...`) AND strictly excluding `đang chuyển`.
   - **COD vs Cart Total Reconciliation:** In-app tracking displays the actual payable COD amount (`Hãy chuẩn bị sẵn <amount>đ tiền mặt`) which often differs from the initial cart item total due to applied platform vouchers/shipping discounts. Always extract and record `cod_amount` alongside `total` to ensure accurate delivery cash preparation. Detect destination hub/bưu cục using Vietnamese and normalized-ASCII keywords. Distinguish “arrived at hub” from “out for delivery”; do not claim pickup availability unless event semantics support it.
8. **Alert on the actionable milestone & Proactive Delivery Watchdog.**
   - **Chống đẩy việc cho User ("Sao mày không canh cho tao?"):** Khi User muốn tự lấy hàng hoặc theo dõi mốc giao, CẤM TUYỆT ĐỐI chỉ đưa link web/hotline rồi bắt User tự F5 canh chừng. Agent BẮT BUỘC chủ động triển khai script watchdog chạy định kỳ (10–15 phút), so khớp state `last_known_time` vs latest event, giữ im lặng khi không có biến động (silent watchdog pattern), và bắn alert khẩn cấp kèm thông tin COD/SĐT ngay khi hàng về bưu cục phát hoặc xuất kho cho shipper.
   - **Anti-App Login Recommendation (Cấm xui tải app khi nhận dùm):** Khi operator/user đi nhận hàng thay cho nick farm hoặc tài khoản proxy, CẤM TUYỆT ĐỐI bảo người dùng "tải app nhà xe và đăng nhập bằng SĐT người nhận". Họ không giữ SIM vật lý để nhận OTP đăng nhập app. Mọi việc theo dõi phải thực hiện qua headless script watchdog hoặc link tra cứu trực tiếp.
   - **Khung giờ vàng gọi bưu cục giữ hàng (07:15 - 08:00 AM) & Bẫy chủ quan hàng nặng:**
     * Không gọi từ đêm hôm trước (hàng còn ở kho tổng SOC/TTKT, bưu cục phát chưa có hàng).
     * **Bản chất "bắn barcode" sáng sớm:** Tem barcode đã dán sẵn trên kiện hàng từ người bán. Việc "bắn barcode" buổi sáng tại bưu cục phát là thao tác shipper tuyến dùng máy quét nhận kiện bốc lên xe máy đi giao.
     * **Cơ hội lấy tại quầy:** Trước khi shipper quét nhận hàng (07:15 - 08:15 AM), kiện hàng đang nằm tại sàn phân loại/quầy bưu cục. Người nhận chỉ cần đọc mã vận đơn và trả COD là lấy được ngay tại chỗ. Sau 08:15 - 08:30 AM khi shipper đã quét và chở đi, quầy không còn hàng nữa.
     * **Bẫy chủ quan hàng nặng/cồng kềnh:** Tuyệt đối tránh suy diễn "hàng nặng shipper chưa ship liền tý lấy cũng được". Tuyến gần bưu cục (< 2-3km), shipper thường chất ngay lên sàn xe chuyến đầu sáng để dọn sàn phân loại.
     * Với đơn hàng dùng SIM ảo/farm không nghe máy được, nếu shipper chở ra đường và gọi không được sẽ bấm hoãn giao/hẹn lại, việc đuổi theo shipper ngoài đường cực kỳ mất công. Khung giờ chuẩn để ra bưu cục lấy hoặc dặn giữ hàng: **07:15 - 08:00 AM**.
   - **Bẫy ghi chú đơn hàng ("Nhận tại bưu cục"):** Dòng "Ghi chú" trên TikTok Shop là cho người bán, shipper không đọc và hệ thống giao hàng tự động vẫn điều phối về địa chỉ nhà. Để chắc chắn 100% giữ hàng tại bưu cục cho các đơn sau, người đặt phải điền thẳng địa chỉ nhận hàng là địa chỉ bưu cục kèm tiền tố `(Khách nhận tại quầy bưu cục)`.
   - **Host Audio Alarms, Dedicated Channel Routing & Zero-Prompt Chat ID Discovery:** Trong môi trường Farm nơi các group Telegram Alert nhận hàng trăm notification mỗi ngày, alert đơn hàng BẮT BUỘC định tuyến vào nhóm Telegram riêng biệt (ví dụ: "Đơn hàng tiktok"). Tuyệt đối CẤM hỏi User mã Chat ID hoặc bảo User gõ `/status`; Agent BẮT BUỘC đọc trực tiếp file `$LOCALAPPDATA/hermes/channel_directory.json` để lấy Chat ID nhóm mới tạo trong O(1).
   - **Continuous Admin Host Siren & Chat Stop Gate:** Với đơn hàng cần ra bưu cục lấy gấp trước ca giao sáng, kích hoạt còi hú liên tục trên máy Admin vật lý (`192.168.110.119`) qua `admin_ssh.py` chạy tiến trình nền `admin_alarm.py <flag_file>` với vòng lặp `winsound.Beep(1200, 250); winsound.Beep(1800, 300)`. Cung cấp cơ chế dừng còi tức thì qua chat: khi User nhắn bất kỳ tin nhắn dừng nào ("dừng", "tắt loa", "stop"), Agent lập tức ghi file cờ `stop_jt_<billcode>.flag` qua SSH để ngắt còi trong < 1 giây.
   - **Farm Voucher Multi-Account Courier Coordination & Secret Keyword Convention:** Bào voucher farm bắt buộc fake tên, SĐT, địa chỉ lệch ngách để né thuật toán cluster fraud của sàn. Để không bị shipper bấm hoàn đơn do không liên lạc được, thiết lập quy ước ngầm với shipper tuyến (hoặc điều phối bưu cục) bằng một "Từ khóa mật mã" in trên phiếu vận đơn. Shipper nhận diện mật mã trên sàn phân loại sẽ tự động gom toàn bộ các đơn về địa chỉ thật của farm để thanh toán COD tiền tươi 1 lần.
   - For local pickup, alert on a destination-hub scan with code, carrier, latest location, and time. Advise contacting the hub to hold the parcel; do not claim the script can prevent courier dispatch unless a hold request is confirmed.
9. **Integrate the dashboard only after the data path works.** Add an orders tab, `/api/orders` endpoint, and image route only after verifying the endpoint returns the canonical record. A rendered card proves UI integration, not live mail or carrier connectivity.
10. **Schedule at a practical cadence.** While waiting for a dispatch code, 15–30 minutes is appropriate for a time-sensitive pickup goal; 12 hours is too coarse. Use script-only/no-agent cron where supported. Keep the script one-shot; do not create an invisible infinite loop.
11. **Verify before reporting DONE.** Run offline parser self-test, one live read when session/credentials are available, inspect JSON state, read the dashboard endpoint back, and report separately: mail session, tracking code, carrier tracking, dashboard, and schedule. Cron status `ok` alone is not proof the script read mail or updated an order.
12. **Unified Order Lifecycle: Three-Phase State Machine, Zero-ADB Web Handoff & Terminal Auto-Retire.**
   - **Phase 1 (`NEED_APP_SYNC`):** New orders without tracking code or unassigned carrier. Inspect in-app TikTok Shop on farm device under `operator_device_lock` using WinRT OCR. Handle the TikTok Shop filter tab trap: if "Không có đơn hàng" appears, tap the "Tất cả" (All) tab to reveal placed COD orders. Immediately upon extracting `tracking_code` and `carrier`, persist to JSON/Excel and transition to Phase 2.
   - **Phase 2 (`ACTIVE_WEB_TRACKING`):** Once a tracking code is present, **STRICTLY DISCONNECT FROM THE FARM DEVICE (Zero ADB / Zero Phone Access)**. Release the phone completely for farm feed/video duties. Track exclusively through carrier Web APIs/pages (J&T Express via billcode + 4-digit recipient phone, SPX API, Ninja Van API). Poll every 10–15 minutes, watching for out-for-delivery, local hub arrivals, and signed deliveries.
   - **Phase 3 (`TERMINAL / RETIRED`):** When the carrier registers final delivery ("Đã giao hàng thành công", "Đã ký nhận", or "Đã hủy"), update canonical JSON/Excel with recipient name and timestamp, then **AUTOMATICALLY RETIRE THE ORDER FROM TRACKING LOOPS PERMANENTLY**. Terminal orders are skipped 100% in subsequent runs—zero ADB calls, zero web requests, zero log noise.
   - **Pure Script Cron Watchdog (`no_agent: true`) Invariant & Anti-Premature Deletion Trap:**
     * **Cấm Xóa Vội Vã Khi Gặp Lỗi ("Sao lại xoá, sửa lại không dùng LLM chứ"):** Khi một cron job theo dõi đơn hàng gặp lỗi (ví dụ HTTP 503 do LLM proxy chập chờn hoặc timeout), TUYỆT ĐỐI CẤM vội vã xóa (remove) cron job khi hệ thống vẫn còn đơn hàng active đang trung chuyển (chưa giao/ký nhận). Thay vì xóa, BẮT BUỘC sửa lại (remediate) thành script thuần `no_agent: true`.
     * **Triệt tiêu LLM Token Bloat & Nghẽn TPM:** Tuyệt đối không bao giờ cấu hình order watchdog dạng Prompt cho LLM (`no_agent: false`). Mỗi tick LLM ngốn 8k–43k context tokens vào prompt hệ thống, làm cạn quota và dính HTTP 503 khi proxy quá tải.
     * **Quy Chuẩn Đường Dẫn Tương Đối & Deploy Wrapper của Hermes Cron:** Hermes Cron từ chối đường dẫn tuyệt đối cho trường `script` (`Script path must be relative to ~/.hermes/scripts/`). Để chạy script nằm tại repo ngoài (ví dụ `D:/Taadaa/orders/watch_jt_delivery.py`):
       1. Viết wrapper script canonical tại `D:\Taadaa\Hermes\deploy\hermes-home\scripts\<script_name>.py` gọi subprocess thực thi script đích.
       2. Kích hoạt `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py` để đồng bộ nguyên vẹn sang `%LOCALAPPDATA%\hermes\scripts\` và OneDrive.
       3. Khởi tạo/cập nhật cron job với `script="<script_name>.py"`, `no_agent=True`, và `workdir="D:/Taadaa/orders"`.
       4. Script tuân thủ watchdog pattern: stdout rỗng khi không có mốc mới (Hermes im lặng 0 token), chỉ in ra khi có mốc bưu cục/shipper giao hàng.
     * **Hook Cơ Học Bảo Vệ Cron:** Bắt buộc `guard_cronjob_safety.py` phải được wire trong `hooks.pre_tool_call` của cả Runtime và Deploy `config.yaml` để chặn đứng tại chỗ nếu agent cố tình tạo cronjob thiếu `no_agent: true`.
   - **Canonical Native Switcher vs WinRT OCR Boundary:** Keep strict separation between UI zones: use Canonical `automation_core.tiktok.account_switcher` (native XML) for Account Switcher / Native Shell to prevent character mistranslations (`0` vs `O`, missing dots in handles), and reserve WinRT OCR Primary exclusively for WebView / TikTok Shop / Order Details screens.
   - **Telegram Channel Targeting via channel_directory.json:** Never prompt the user for group Chat IDs. Order tracking alerts must route directly to the designated order channel (e.g. `telegram:-5316882628`), resolved via `$LOCALAPPDATA/hermes/channel_directory.json`.
   - **Anti-Kneejerk Removal on HTTP 503 Overload:** When an order tracking cron encounters temporary proxy failures (`HTTP 503: Service temporarily unavailable: all targets were skipped by pre-dispatch filters`), NEVER remove the cron job when active orders remain in transit. Remediate it immediately to pure script `no_agent: true` with a canonical wrapper in `hermes/scripts/`.

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

- `references/zero-token-cron-wrapper-and-guard-wiring.md` — Zero-token cron watchdog wrapper pattern (`no_agent: true`), relative script path resolution via `deploy/hermes-home/scripts/`, anti-kneejerk deletion on HTTP 503, and mandatory 9 pre-tool hooks runtime/deploy parity.
- `references/multi-carrier-ghn-spx-jt-api-and-lifecycle-routing.md` — Multi-carrier reverse-engineering (GHN public API with phone_verify, J&T Express cellphone validation, SPX/Ninja Van APIs), normalized status milestones, and zero-ADB handoff.
- `references/in-app-tracking-extraction-and-switcher-disambiguation.md` — Profile handle ambiguity vs switcher sheet trap, J&T 12-digit numeric billcode pattern, double device-lock deadlock avoidance, and terminal retirement protocol.
- `references/order-lifecycle-state-machine-and-auto-retire.md` — 3-phase state machine (In-app discovery -> Zero-ADB web tracking -> Terminal retirement), pure script watchdog pattern (`no_agent: true`), and native vs webview boundary rules.
- `references/farm-voucher-order-logistics-and-jt-tracking.md` — J&T web tracking 4-digit phone validation trick, farm voucher anti-app-download rule, multi-shipper route coordination, secret keyword convention, and host audio alarm pattern.
- `references/jt-express-carrier-tracking-and-pickup-watchdog.md` — J&T Express reverse-engineering, zero-prompt Telegram group discovery via channel_directory.json, continuous Admin host siren with chat stop gate, and farm voucher courier coordination protocol.
- `references/order-mail-to-carrier-handoff.md` — mailbox discovery, profile disambiguation, dedup state, carrier handoff, and evidence labels.
- `references/order-card-image-integrity.md` — preserve raw image aspect ratio and zoom links on order dashboards.
- `references/shopclone7-boxtaikhoan-order-audit.md` — ShopClone7/BoxTaiKhoan order retention reality vs 3-day UI warning, API 404 behavior, and host Chrome login session.
- `references/tiktok-in-app-order-tracking.md` — In-app order inspection protocol, device locking, account verification, and carrier handoff.
- `references/jt-express-tracking-and-farm-order-governance.md` — J&T Express web tracking (anti-scraping 4-digit phone bypass, event parsing), farm voucher pickup protocol (no-app rule, courier bundling, hub morning window 07:15–08:00, secret order-note convention), and host audible alarm pattern.
- `references/tiktok-shop-order-creation-and-cross-reference-audit.md` — Creation of canonical order records from user farm desktop screenshots, device and account cross-referencing, image cropping, and multi-store atomic synchronization.
