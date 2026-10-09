# Mobile Responsive Fleet Dashboard Design Patterns

## Overview
When operators access local web tools or social media farm fleet dashboards (e.g., running via Python `ThreadingHTTPServer` or local Node/Next.js) on mobile devices (iOS Safari, Android Chrome), dense multi-column desktop tables and unpadded headers cause severe usability issues.

## Key Usability Failures on Mobile
1. **Dynamic Island / Hardware Notch Clipping:**
   - Top banners and guidelines are obscured by camera cutouts if `<meta name="viewport">` lacks `viewport-fit=cover` or CSS does not use `env(safe-area-inset-top)`.
2. **Dual-Axis Scroll Traps:**
   - Wide tables (15-20 columns, `min-width: 760px`) placed inside `overflow-x: auto` containers intercept vertical scrolling gestures on mobile touchscreens. When an operator tries to scroll down, the touch event is captured as horizontal drag, causing the page to feel stuck or jittery.
3. **Loss of Context on Horizontal Pan:**
   - Scrolling right across historical date columns hides the Machine ID and Username columns, making it impossible to identify which account a data cell belongs to.
4. **Vertical Real Estate Hogging:**
   - Analytical breakdown cards (e.g. Quota guidelines, Sweet Spot distributions) can consume 500-600px vertically, pushing the actual actionable account list completely off the initial mobile viewport.

---

## Canonical Solutions

### 1. Viewport & Safe-Area Inset Hardening
In `<head>`:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
```

In `<style>`:
```css
body {
    padding-top: max(16px, env(safe-area-inset-top));
    padding-bottom: max(16px, env(safe-area-inset-bottom));
    padding-left: max(12px, env(safe-area-inset-left));
    padding-right: max(12px, env(safe-area-inset-right));
}
```

### 2. View Toggle Pattern: [📱 Thẻ Di Động] vs [📊 Bảng Ma Trận]
Instead of trying to squeeze a 18-column table into a 390px phone screen:
- Provide an explicit toggle button or auto-switch based on `@media (max-width: 768px)`.
- Default to **Card View** on mobile devices.

#### Mobile Card Structure
Each account is rendered as a self-contained card:
- **Header:** Machine `M<id> (Row <row>)` | Proxy Port `:port (🔗Partner)` | Tier status badge (`Khỏe` / `Cooldown` / `Hồi phục`).
- **Account Info:** `@username` link, modal history button, cumulative metrics (`Tổng`, `TB/ca`, `Max Safe`).
- **Mini Timeline Strip:** The last 6–7 run dates rendered as a compact inline row of pill chips:
  ```html
  <div class="mini-timeline">
      <span class="chip chip-safe" title="2026-10-09: 14 safe">+14</span>
      <span class="chip chip-drop" title="2026-10-08: Drop 15">🛑 15</span>
      <span class="chip chip-rest" title="2026-10-07: Rest">-</span>
  </div>
  ```
  *Benefit:* Operators can assess an account's recent performance trajectory instantly without any horizontal scrolling!

### 3. Sticky Multi-Column Freezing for Wide Tables
When Table View is explicitly chosen on mobile or tablet:
```css
/* Freeze Machine column at left: 0 */
th:nth-child(1), td:nth-child(1) {
    position: sticky;
    left: 0;
    background: #0f172a;
    z-index: 2;
    min-width: 70px;
    border-right: 1px solid #334155;
}

/* Freeze Username column next to Machine */
th:nth-child(2), td:nth-child(2) {
    position: sticky;
    left: 70px;
    background: #0f172a;
    z-index: 2;
    min-width: 130px;
    border-right: 1px solid #334155;
}
```

### 4. Collapsible Secondary Analytics
Wrap high-height analytical cards in `<details>` or toggleable accordions:
```html
<details class="fleet-panel-collapsible">
    <summary class="fleet-panel-title">🎯 Vùng An Toàn & Khuyến Nghị Quota (Chạm để xem chi tiết)</summary>
    <div class="analytics-content">
        <!-- High-density charts or quota guidance here -->
    </div>
</details>
```
On desktop, keep `<details open>`; on mobile, default closed to allow direct access to operational accounts.
