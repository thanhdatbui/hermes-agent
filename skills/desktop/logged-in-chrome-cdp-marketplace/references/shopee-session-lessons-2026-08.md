# Shopee session lessons (historical)

This file records reusable failure patterns from a Shopee comparison session. It is not current marketplace data; re-verify every product, price, variant, rating, sales count, stock, shipping fee, and voucher live before reporting.

## User corrections that must control the workflow

- “Shopee” means search inside Shopee, not Google or search-engine snippets.
- Honor the requested surface: browser plugin, `computer_use`, and CDP are separate modes. A failure in one mode does not authorize silently switching to another.
- The user wants a short Vietnamese report with direct product links and exact live facts. Do not narrate internal tooling or claim an action succeeded from a click, toast, cart badge, or remembered page alone.
- For this use case, the target is transparent/amber Kapton around phone-box battery/power cables: compare exact width (usually 10mm), length, adhesive/heat/electrical suitability, reviews/sales, current variant price, and delivered cost.

## Reusable verification lessons

- A cheaper domestic listing can beat an initially supplied international listing; rank verified fit, evidence, and current delivered cost rather than anchoring on the first URL.
- A product detail page can show a price range across variants. Report the price only after selecting and verifying the exact requested variant; never report the range as the 10mm price.
- “Vui lòng chọn phân loại hàng” means the variant selection failed. Verify the selector text and selected state before adding to cart.
- Cart badge increments, a toast, or a scripted click do not prove addition. Inspect the cart row for exact title, variant, price, and direct item link.
- Voucher availability is not voucher application. Check minimum order, shipping mode, product/category restrictions, app/video/live restrictions, and account prerequisites; SPayLater is ineligible when activation is required.

## Tool-specific blocker patterns

- Browser/plugin navigation may receive Shopee `/verify/traffic/error` with `is_logged_in=false`; report the blocker for that surface instead of using Google as a fallback.
- `computer_use` can report 0×0 or no visible window even when the diagnostic command says the driver/UIAutomation is healthy. Treat this as an unavailable live surface, preserve the browser/cart state, and report `BLOCKED/UNVERIFIED`; do not claim a search or click occurred.
- If a future session needs recovery, diagnose/restart only the requested tool surface under its own troubleshooting procedure; do not replace it with an unauthorized surface.

## Historical candidate evidence (not current)

One verified live CDP detail page in the session showed a domestic Kapton/polyimide listing:

- Shop: Linh kiện Điện tử Quang Minh
- Direct item: `https://shopee.vn/...-i.1119058626.25711375070`
- Exact variant: `rộng 10mm dài 33 mét`
- Then-visible price: `23.500₫`
- Then-visible rating/sales: `4.9`, `465` reviews, `2k+` sold
- Then-visible stock/spec: `CÒN HÀNG`; polyimide, silicone adhesive, 0.05mm, described as 160–320°C and for lithium-battery/PCB insulation

These values are historical evidence for the session only and must never be presented as current without a fresh live Shopee check.
