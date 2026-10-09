# TikTok Account Switcher Open Flow & Sticky Header Invariants

## Canonical Opening Sequence (User Design)
On modern TikTok builds (v46.x+ across all farm devices):
1. **Navigate to Personal Profile (`Hồ sơ`)**:
   Tap the bottom navigation tab (`x ≈ 972, y ≈ 1857` on 1080x1920).
2. **Scroll Profile First to Anchor Sticky Header**:
   Perform a gentle upward swipe (`swipe 540 1000 540 700 250ms`, ~300px).
   This causes the profile username/ID to scroll up and lock onto the top-center sticky header bar (`pmi` / `pmf` / `pcs` / `pq2` / `r2b`).
   *CRITICAL PITFALL*: DO NOT tap the display name or @handle in the middle body of the profile before scrolling. Tapping the body frequently opens edit profile, triggers bio input/keyboard dialogs, or hits unclickable text views.
3. **Tap Directly on Pinned ID at Top Center**:
   Tap coordinates: `(sw // 2, 150)` (e.g., `x ≈ 511-540, y ≈ 150-156` on 1080p, bounds `[368, 132][654, 179]`).
   This cleanly triggers TikTok to open the `Chuyển đổi tài khoản` (Account Switcher) bottom sheet.
4. **Scroll Sheet & Add Account**:
   To add a new account, scroll the bottom sheet down to reveal the `Thêm tài khoản` (`Add account`) button at the bottom.

## Samsung Pay Bottom Edge Conflict Guard
On Samsung Galaxy S7 (SM-G930) and similar devices with the Samsung Pay Quick Pay bar (`[300, 1893][780, 1920]`):
- NEVER initiate vertical swipes from `y >= 1600` or below `1350`. Swiping up from the bottom edge pulls up Samsung Pay, causing TikTok to collapse to the background (Home screen).
- Safe swipe bounding box: `y ∈ [450, 1350]`.
- For scrolling settings or switcher lists: use `swipe 540 1350 540 450 350`.

## Anti-Patterns
- CẤM tự ý chế flow "Đăng xuất" (logout) khi switcher không bung ngay. Luôn tuân thủ quy trình cuộn profile trước để ghim ID lên đỉnh rồi tap ID.
- CẤM bấm tay ADB thay cho việc chuẩn hóa selector và quy trình tự động.
