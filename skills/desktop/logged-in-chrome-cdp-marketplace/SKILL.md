---
name: logged-in-chrome-cdp-marketplace
description: Use the user's already-configured, logged-in Hermes Chrome CDP profile for Shopee and other marketplace research. Trigger whenever the user says to search Shopee/marketplaces via the saved Chrome/CDP account.
version: 1.0.0
author: Hermes Agent
platforms: [windows]
tags: [chrome, cdp, shopee, marketplace, logged-in-profile]
---

# Logged-in Hermes Chrome CDP for Marketplace Research & User Browser Inspection

## User-specific profiles & CDP setup

1. **User Main Chrome Profile (Kal - `jinrakal@gmail.com`):**
   - User Data Dir: `C:\Users\Kibe\AppData\Local\Google\Chrome\User Data`
   - Profile Subdirectory: `Profile 4`
   - Chứa toàn bộ phiên đăng nhập thật của User (BoxTaiKhoan, Shopee, mạng xã hội, lịch sử mua hàng cá nhân).
   - **Khi User yêu cầu dùng Chrome chính của User qua Remote Debugging / CDP:**
     - Đóng các tiến trình Chrome cũ: `powershell.exe -Command "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"`
     - Khởi chạy lại Chrome chính đính kèm cổng CDP 9222:
       `powershell -Command "Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--remote-debugging-port=9222', '--user-data-dir=\"C:\Users\Kibe\AppData\Local\Google\Chrome\User Data\"', '--profile-directory=\"Profile 4\"'"`
     - Kết nối CDP qua `http://127.0.0.1:9222/json/version` để tương tác trực tiếp trên profile chính của user.

2. **Hermes Isolated Browser Profile:**
   - User Data Dir: `C:\Users\Kibe\AppData\Local\hermes\browser_profile`
   - Profile Subdirectory: `Default`
   - Dùng cho các tác vụ crawl/tách biệt không đụng chạm đến profile cá nhân.

## Mandatory operating rule

When the user asks to search Shopee or another marketplace:

1. **Prioritize CDP immediately:** Connect directly to the user's running Chrome CDP session (`127.0.0.1:9222`) first. Do NOT run external web search / curl search or guess snippets when the user asks for Shopee marketplace items.
2. Check the live CDP endpoint first:
   - `curl -s http://127.0.0.1:9222/json/version`
   - `curl -s http://127.0.0.1:9222/json/list`
3. Connect to the existing non-headless Hermes Chrome instance over CDP. Use its current context/profile and reuse/create a tab in the authenticated session (`jinrakal`).
4. Never create a separate headless Chrome, temporary profile, or regular Chrome profile for the task. Never use Google snippets as a substitute while claiming the data came from Shopee.
5. Never read, decrypt, export, or print cookies, passwords, tokens, or account credentials. Use the live authenticated browser context only.
6. Do not close the user's browser or browser context. Close only a temporary tab created by this task after verification, unless the user asks to leave it open.

## If CDP is unavailable

- First inspect Chrome processes/ports to find the actual Hermes CDP endpoint; do not assume a different profile is equivalent.
- If the Hermes CDP instance is not running, launch only the Hermes profile, visibly and detached:
  - CMD: `cmd.exe /c start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\Kibe\AppData\Local\hermes\browser_profile" --profile-directory=Default`
  - PowerShell (nếu CMD bị lỗi parse argument): `powershell -Command "Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--remote-debugging-port=9222 --user-data-dir=\"C:\Users\Kibe\AppData\Local\hermes\browser_profile\" --profile-directory=Default'"`
- TUYỆT ĐỐI KHÔNG dùng cờ `--headless` hay tạo subprocess background đè làm lock profile và trigger WAF.
- Sau khi khởi chạy, verify `curl -s http://127.0.0.1:9222/json/version` và `curl -s http://127.0.0.1:9222/json/list` trước khi gửi lệnh.
- Khi điều hướng sang item Shopee: dùng `document.location.href` trên tab đã có sẵn của phiên đăng nhập (`jinrakal`), click chọn đúng button phân loại (variant) trên DOM để kiểm tra trạng thái Còn Hàng/Hết Hàng và số lượng Đã Bán. CẤM tự ý search Google rồi fake số liệu trả về.

## Shopee search & item discovery patterns

1. **Shopee Search DOM Lazy-render Pitfall:**
   - Trên trang tìm kiếm `shopee.vn/search?keyword=...`, Shopee dùng React lazy-rendering và skeleton placeholder, `document.querySelectorAll('a[href*="-i."]')` thường chỉ trả về 3-4 item banner/quảng cáo của shop đề xuất thay vì danh sách kết quả đầy đủ.
2. **In-session Fetch API (Đáng tin cậy nhất):**
   - Chạy `fetch('/api/v4/search/search_items?by=relevancy&keyword=' + encodeURIComponent(kw) + '&limit=20&newest=0&order=desc&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2')` trực tiếp trong context tab Shopee đã đăng nhập qua `Runtime.evaluate`.
   - Lấy danh sách item chính xác: `name`, `shopid`, `itemid`, `price` (/100000), `historical_sold`, `item_rating.rating_star`.
   - Điều hướng trực tiếp đến từng sản phẩm bằng `https://shopee.vn/product/{shopid}/{itemid}` để kiểm tra mô tả kỹ thuật (OFC pure copper, AWG gauge, phân loại độ dài, tình trạng kho).

## Shopee research & Cart/Voucher workflow

1. Use the logged-in CDP page and navigate to Shopee normally.
2. Prefer the normal visible Shopee search UI/DOM flow: search box, keyword, Enter, wait for results.
3. Open each candidate's direct Shopee item page in the same authenticated context.
4. **Variant Selection Mechanics:**
   - Multi-variant items: Kiểm tra thuộc tính `aria-disabled` trên các nút phân loại (`button`). Nút có `aria-disabled="true"` hoặc class chứa `Dbg4vL xJKrxj` là phân loại **HẾT HÀNG / BỊ KHÓA** — không click được (nếu cố bấm Mua Ngay/Thêm Giỏ sẽ hiện toast "Vui lòng chọn phân loại hàng").
   - Nút khả dụng (`aria-disabled="false"`): Sau khi click sẽ chuyển sang class `selection-box-selected`.
   - Single-variant items (không có nút phân loại): Có thể bấm trực tiếp `Thêm Vào Giỏ Hàng` hoặc `Mua Ngay`.
5. Extract only data visible on the live Shopee page/DOM for the selected variant: item title, exact variant (e.g. 10mm), price, roll length, sold count, rating, stock if shown, seller/shop, and direct item URL.
6. **Cart & Voucher Inspection Workflow:**
   - Điều hướng `https://shopee.vn/cart`.
   - Tìm dòng sản phẩm cần mua và tích checkbox (`label` hoặc `input[type="checkbox"]`).
   - Bấm vào hàng `Shopee Voucher - Chọn hoặc nhập mã` ở footer.
   - Đọc danh sách voucher trong `div[role="dialog"]` / popup (kiểm tra voucher Freeship, Voucher Xtra, Giảm giá & Hoàn Xu).
   - Bấm `ĐỒNG Ý` để áp dụng voucher vào đơn hàng và đọc tổng tiền cuối cùng.
7. Never infer a Shopee price or stock from Google result snippets, cached pages, URL text, or a different variant.
8. If Shopee redirects to `/verify/traffic`, `/verify/captcha`, or another WAF page, report that the authenticated live page is blocked. Do not silently replace the source with Google and do not present snippet data as live Shopee data.
9. If a captcha appears, do not bypass or solve it automatically. Leave the page state intact and ask the user to complete it manually if needed; then continue through the same CDP session.

## Interaction-mode and recovery discipline

- Honor the user's requested control surface exactly. `browser plugin` means use `browser_*` only; `computer use` means use `computer_use` for interaction; CDP means the existing authenticated CDP session. Do not silently switch modes or report a result obtained through a different surface as if it came from the requested one.
- Before computer-use interaction, take a fresh SOM/AX capture and verify the Chrome target. If capture is `0x0`, empty, or the app cannot be found, do not click blindly. Run `hermes computer-use doctor`, check the real window separately, and retry only after the target is identified.
- If the user authorizes restarting the browser, identify the PID listening on port `9222` and verify its command line contains both `--remote-debugging-port=9222` and the exact Hermes profile path `C:\Users\Kibe\AppData\Local\hermes\browser_profile`. Kill only that verified process tree; relaunch visibly with the same profile and port. Then verify `/json/version`, `/json/list`, and the requested surface before continuing. Never kill unrelated Chrome windows.
- A successful CDP navigation or DOM read proves only that CDP worked; it does not prove computer use worked. Report the actual surface used. If the requested surface remains unavailable, label that path `BLOCKED` rather than substituting another surface or inventing an interaction result.
- Preserve the user's state: do not close unrelated Chrome windows, alter unrelated cart rows, or launch a second profile to evade WAF.

## Candidate selection, evidence, and user-scope gates (mandatory)

### Search-source discipline

- If the user says Shopee, search and compare **inside the live Shopee session only**. Never use Google, marketplace snippets, cached pages, generic web results, old session data, or remembered prices as a substitute while claiming the data came from Shopee.
- Respect the requested tool surface exactly: `browser plugin` means browser tools only; `computer use` means `computer_use` only; CDP means the existing authenticated CDP session only. Never silently switch surfaces after a block or failure.
- A user screenshot or remembered listing may be used as a lead, but every recommendation must be re-verified on the requested live Shopee search/detail page before it is called the best choice.
- A WAF result, `verify/traffic`, `is_logged_in=false`, missing product cards, 0×0 capture, or missing window on the requested surface is a blocker for that surface. Report `BLOCKED/UNVERIFIED`; do not substitute another source, old data, or a guessed result.
- If the user corrects the source, shop, product, or tool, stop the current path and restart verification from the corrected source/tool instead of defending or reusing the earlier result.

### Compare before recommending

1. Extract the physical requirement: width, approximate length, transparency, adhesion/removability, heat/electrical suitability, and whether the tape is for inspection or permanent mechanical restraint.
2. Search Shopee for multiple candidates (normally at least three when available), then open each candidate's **direct Shopee item page**.
3. For each candidate, record only live evidence: shop, direct item URL, exact selected variant, price for that variant, length, rating/review count, sold count, stock, shipping origin/ETA, and visible voucher conditions.
4. Reject candidates with missing variant/price/stock evidence. Rank the remaining candidates on fit first, then rating/sales/reliability, then delivered cost—not on the first listing opened or the link initially supplied by the user.
5. Recommend one winner and at most one fallback, with a short reason. Do not recommend an international/expensive listing merely because it was already open if a verified domestic equivalent is better.

### Variant and cart proof

- A tap/click is not proof. After selecting a variant, verify the UI shows the exact requested option (for example `rộng 10mm dài 33 mét`) and the selector changes to its selected state. If Shopee displays `Vui lòng chọn phân loại hàng`, selection failed; fix it before adding anything and never report it as selected.
- After adding to cart, verify the actual cart row contains the target title, exact variant, exact price, and matching direct item URL. A cart badge increment, toast, or button click alone is insufficient.
- Preserve unrelated cart items. Select only the target row for any cart/voucher inspection; never use `Chọn Tất Cả` on a user's existing cart.

### Voucher and checkout boundaries

- A voucher being listed is not the same as being applicable or applied. Check minimum spend, shipping mode, product/category, app-only/video/live restrictions, and account prerequisites. Treat `SPayLater` vouchers as ineligible when the live page says the account is not activated.
- After clicking `ĐỒNG Ý`/`ÁP DỤNG`, verify the voucher name and resulting savings/total in the cart or checkout summary. If the total does not change, report it as not applied.
- Keep these fields separate in the report: item price, shipping fee, voucher/discount, and final pre-payment total. Do not invent shipping or voucher savings from a cart page that has not calculated them.
- Adding to cart and inspecting/applying a voucher is allowed only when the user asked for it. Never click `Mua Hàng`, `Đặt hàng`, `Thanh toán`, or an equivalent final-order/payment control without explicit fresh authorization; when scope is only “thêm vào giỏ”, stop at the verified cart row.

### Reporting style for this user

- Write in concise Vietnamese, direct and readable; no internal workflow narration, no emojis, no invented certainty, and no claim of a completed click/action without verification.
- For comparisons, use one compact row/block per candidate: direct Shopee link, shop, exact variant, current price, length, rating/review count, sold count, stock, and shipping/voucher only when visible live. Mark missing fields `UNVERIFIED`; never show rough ranges as current prices.
- Rank fit first, then evidence quality/reviews/sales, then price. Do not recommend the first opened or previously supplied link when a verified domestic equivalent is better.
- Keep item price, shipping, voucher/discount, and pre-payment total separate. A listed voucher is not an applied voucher.
- When blocked, report only the blocker and the verified facts already obtained; do not pad the answer with theory or substitute-source explanations.

## Add to Cart & Checkout Limitations (Anti-bot / isTrusted)

- **CDP script clicks (dispatchMouseEvent / element.click()):** Frontend React của Shopee chặn các request POST ngầm `/api/v4/cart/add_to_cart` khi event mang cờ `isTrusted = false`.
- **Thao tác giỏ hàng/thanh toán:** Điều hướng trực tiếp đến trang chi tiết sản phẩm trên cửa sổ Chrome CDP đang chạy của user và hướng dẫn user click tay 1 chạm để thêm giỏ/áp voucher, tránh làm phát sinh cờ bot/block tài khoản Shopee thật.

## Verification gate before reporting

- Confirm the final URL is a real Shopee item URL matching `shopee.vn/...-i.<shop_id>.<item_id>`.
- Confirm the displayed variant matches the requested width/length.
- Confirm price and sold count came from the live item page, not a search-engine result.
- If any gate fails, label the result `BLOCKED/UNVERIFIED` and do not recommend a purchase from it.

## References

- `references/shopee-session-lessons-2026-08.md` — reusable lessons from the Kapton comparison: exact-source/tool-surface discipline, WAF/0×0 blockers, variant/cart/voucher proof, concise reporting, and historical evidence boundaries.
