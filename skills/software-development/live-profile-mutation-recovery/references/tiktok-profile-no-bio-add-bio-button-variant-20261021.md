# TikTok Profile Variant: "Chưa Có Tiểu Sử" (+ Thêm Tiểu Sử vs Find Friends Trap)

## Context & Incident (2026-10-21)
During batch rename on Machine 4 (account `@votam5319`), the runner consistently failed with `reason="vuot qua 35 buoc"` despite having a working rename runner.

## Root Cause Analysis
1. **Layout Difference:**
   - On accounts that already have a bio, TikTok S7 displays either:
     - A text button "Sửa hồ sơ" at center-screen, OR
     - A pencil icon on the top-left toolbar `(72, 148)`.
   - On accounts that **do NOT have a bio yet** (e.g. `@votam5319`):
     - The text button "Sửa hồ sơ" is **absent**.
     - Instead, two buttons are displayed side-by-side at Y ≈ 840–890:
       - Left: `+ Thêm tiểu sử` (X: 162 to 468, Y: 844 to 882)
       - Right: `Liên hệ với tôi...` (X: 519 to 896, Y: 849 to 890)
     - The top-left toolbar `(72, 148)` is **NOT a pencil**, but the **Find Friends** icon (`Tìm bạn bè`).

2. **The Ping-Pong Trap:**
   - Because "Sửa hồ sơ" was missing, the runner fell back to tapping `XY_EDIT_PENCIL = (72, 148)`.
   - Tapping `(72, 148)` opened the "Tìm bạn bè" dialog.
   - The runner classified "Tìm bạn bè" as `FEED` (because it contained suggested accounts: "Tài khoản được đề xuất").
   - In state `FEED`, the runner tapped the bottom-right tab `XY_PROFILE_TAB = (972, 1857)`.
   - On "Tìm bạn bè", the bottom navigation bar is not visible, so the tap did nothing or triggered video playback in background.
   - The next state was `UNKNOWN`, which triggered `keyevent(4)` (BACK).
   - BACK returned to "Tìm bạn bè", which again triggered `FEED` -> tap profile -> `UNKNOWN` -> BACK -> repeat until reaching step 35.

## Resolution & Invariant Rule
1. **Dynamic Button Detection:**
   When in `PROFILE` state attempting to enter `EDIT_PROFILE`, always search for both the standard edit button and the bio button:
   ```python
   btn = (find_box(boxes, r"(sua|chinh sua|edit)\s*(h[o0]|profile)") or 
          find_box(boxes, r"\+\s*th[eé]m|tid\w{0,2}\s*s|th[eé]m\s*ti|tieu\s*su"))
   xy = center(btn) if btn else XY_EDIT_PENCIL
   tap(xy, 4)
   ```
   Tapping `+ Thêm tiểu sử` opens the full `EDIT_PROFILE` screen (allowing modification of both Name and Bio).

2. **Watchdog Re-queue Guarantee:**
   - Accounts failing due to UI traps or cold-boot delays are NOT written into `rename_natural_state.json`.
   - In the next 15-minute watchdog tick, they are automatically selected as eligible targets and retried.
