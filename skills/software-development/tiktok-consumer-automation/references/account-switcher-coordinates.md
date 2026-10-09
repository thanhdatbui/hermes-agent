# TikTok Account Switcher Coordinates & Fallback

## Profile Header Switcher Dropdown
- **Chuẩn TikTok 46.x (Samsung Galaxy / S7 / 1080x1920)**:
  - Top header bar anchor dropdown switcher: `(539, 140)`.
  - Không dùng toạ độ giữa màn hình `(540, 552)` vì đó là username / display name giữa trang thay vì top dropdown toggle.
- **Áp dụng trong code**:
  - `TikTokAdapter.coordinate_fallback("switcher")` -> trả về `(539, 140)`.
