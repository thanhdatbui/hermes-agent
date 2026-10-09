# Machine 266 Profile Dropdown Defect & Overlay Dismiss Pattern (Case REG-25)

## Defect Summary
On Samsung Android devices (e.g. machine 266), TikTok profile UI introduces overlay widgets such as `q3t` ("Bạn đang nghĩ gì...", "What's on your mind") located near `[200, 180][880, 240]` (center roughly `(540, 210)`).

## Failure Mechanism
1. In `_try_open_account_dropdown_once` (Pass 4: display name fallback), matching against general header text without filtering `q3t` taps directly at `(540, 210)`.
2. This tap triggers the camera / video creation overlay ("TẠO", "ĐĂNG", "LIVE", "Video mới").
3. Subsequent dropdown retries fail because the app remains trapped on the camera/create overlay surface.
4. Fallback `_open_account_dropdown_via_settings` attempts to tap `(1005, 150)` (Profile Menu), which hits "Video mới" instead, causing `[03_dropdown] Khong mo duoc account dropdown`.

## Resolution & Contract
1. **Pass 4 Blacklist**:
   - Resource IDs: include `"q3t"`.
   - Text filters (lowercased / stripped): include `"bạn đang nghĩ gì"`, `"ban dang nghi gi"`, `"what's on your mind"`.
2. **Overlay Dismissal in `dismiss_profile_overlays`**:
   - Detect camera/create screen via:
     - Keywords: `"video moi"`, `"bai hat lan truyen"`, `"mau tho bay mau"`, or combination of `"dang"`, `"tao"`, `"live"`.
     - Resource ID: `"h7l"`.
   - Dismiss action:
     - Prefer semantic dismiss: `find_text_tap(device_id, "Đóng", "Dong", "Close")`.
     - Fallback: coordinate tap `(84, 150)` and `keyevent 4` (BACK).
3. **Fail-Closed Contract**:
   - Retain explicit `raise RuntimeError("[03_dropdown] Khong mo duoc account dropdown")` when dropdown cannot be opened.
