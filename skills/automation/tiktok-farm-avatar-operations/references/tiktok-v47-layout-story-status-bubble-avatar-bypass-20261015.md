# TikTok v47.0.3 Profile Layout Pitfall: Status Note Bubble & Story Overlay Bypass (15/10/2026)

## 1. Problem Description
On newer TikTok Android builds (v47.0.3+), accounts encounter an altered profile header layout:
1. **Avatar Position:** The avatar is placed in the top right (`bounds: [708,246][1080,636]`).
2. **Status Note Bubble ("Trà hay cà phê?", "Bạn có tin vui?"):** Overlays the upper half of the avatar (`bounds: [763,258][1037,465]`). Tapping near the avatar center or upper half opens the "Tám chuyện nào" status input sheet and raises the Android software keyboard instead of the avatar editor.
3. **Story / Nhật ký Overlay (+ icon):** Sits on the bottom-right of the avatar (`bounds: [931,499][1080,636]`). Tapping it opens the camera / Story picker.
4. **Missing Rectangular Edit Buttons:** The traditional `[ Sửa hồ sơ ]` and `[ Chia sẻ hồ sơ ]` buttons below the follower stats are absent or pushed below the fold.
5. **False Positive "Done" Reports:** Scripts that blindly tap avatar coordinates without verifying the resulting screen or crop screen will fail silently, leaving the old avatar intact.

---

## 2. Robust Resolution Path: Top-Left Pencil Entry

Instead of attempting to click through the overcrowded avatar bounds or status note bubble, use the top-left navigation pencil icon:

### Step-by-Step UI Flow
1. **Navigate to Profile:** Tap the bottom tab `Hồ sơ` at `(972, 1857)` and wait 2.5s.
2. **Open "Sửa hồ sơ" via Top-Left Pencil:**
   - On this layout, an edit pencil icon is located at the top-left bar (`bounds: [24,96][126,204]`).
   - Tap `(75, 150)`.
   - Verify screen has text `'Sửa hồ sơ'` and `'Thay đổi ảnh'`.
3. **Open Avatar Bottom Sheet:**
   - Tap `'Thay đổi ảnh'` at `(540, 580)`.
   - Wait 2.0s for the bottom sheet `['Chụp ảnh', 'Tải ảnh lên', 'Xem ảnh']` to open.
4. **Select "Tải ảnh lên":**
   - Tap `'Tải ảnh lên'` at `(540, 1637)`.
5. **Pick Recent Avatar:**
   - Ensure target image was pushed to `/sdcard/Pictures/` and MediaStore scanned (`am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE`).
   - In Photo Picker, tap the first tile at `(215, 276)`.
   - Tap `'Tiếp'` at `(1000, 1850)`.
6. **Crop & Save:**
   - Wait 3.5s for the Crop screen (`Cắt`, `Xem trước`, `Hủy`, `Lưu`).
   - Tap `'Lưu'` at bounds `[552,1728][1032,1860]` (center: `(792, 1794)`).
   - Wait 6.0s for upload completion.
7. **Return & Verify:**
   - Tap back arrow at `(84, 78)` or send `keyevent 4` to return to Profile.
   - Do NOT assume success: run face detection / image comparison on the live screencap to prove the new human face is present before reporting DONE.

---

## 3. Account Switcher Collision & Device-Lock Preflight

- When farm background processes (`multi-machine-feed-session`) run on the machine, `run_tiktok_upload_avatar.ps1` batch runner skips the target due to active device lock (`SKIPPED_LOCKED`).
- If feed sessions switch the active account to another slot (e.g. `@voyen065`), always verify the current username before initiating avatar change:
  - If switched, tap username/display name header `(200, 300)` to open Account Switcher, select target account, and return to Profile tab before proceeding.
