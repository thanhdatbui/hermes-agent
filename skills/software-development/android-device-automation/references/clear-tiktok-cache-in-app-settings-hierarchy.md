# TikTok Cache Clearing & Storage Management Standard

## 3-Tier Hierarchy for Clearing TikTok Cache (`clear-tiktok-cache.py`)

To safely reclaim gigabytes of disk space across farm devices without risking account data loss (`pm clear` is strictly forbidden):

### 1. Tier 1: Deep Link Intent (Fastest)
- Intent commands:
  ```bash
  am start -a android.intent.action.VIEW -d 'snssdk1180://clean_cache' com.ss.android.ugc.trill
  # fallback secondary scheme:
  am start -a android.intent.action.VIEW -d 'snssdk1233://clean_cache' com.ss.android.ugc.trill
  ```
- If supported by the installed TikTok build, this lands directly on the "Giải phóng dung lượng" (Free up space) screen within 2-3s.

### 2. Tier 2: In-App Settings Navigation Fallback (Universal)
When deep links fail or are not handled by the active TikTok activity router:
1. **Launch TikTok**:
   - `input keyevent KEYCODE_WAKEUP && wm dismiss-keyguard && input keyevent KEYCODE_MENU`
   - `monkey -p com.ss.android.ugc.trill 1`
   - Poll UI until interactive (Profile / Home tabs visible).
2. **Navigate to Profile Tab**:
   - Tap "Hồ sơ" / "Profile" node (`res-id` containing `o1m`/`ofe` or bottom-right coordinate `972, 1857`).
3. **Open 3-Bar Menu (Top-Right)**:
   - Tap "Menu hồ sơ" / "Thêm tùy chọn" / "More options" (`bounds` at top right `x >= 700, y <= 300` or fallback `1002, 150`).
4. **Open Settings**:
   - Tap "Cài đặt và quyền riêng tư" / "Settings and privacy" / "Cài đặt" (`bounds` around center `621, 1260`).
5. **Find & Open "Giải phóng dung lượng"**:
   - Swipe up from `(540, 1500)` to `(540, 500)` in a bounded loop (up to 6-8 swipes).
   - Tap the node matching "Giải phóng dung lượng" / "Free up space".
6. **Clear Cache on Storage Screen**:
   - Locate the "Bộ nhớ đệm" (Cache) row.
   - Tap the "Xóa" (Clear) button specifically on the "Bộ nhớ đệm" row (NEVER tap "Tải về" / Downloads).
   - On the confirmation dialog ("Xóa bộ nhớ đệm?"), tap the confirm "Xóa" button.
   - Verify cache reaches `0,0MB` or `0.0MB`.
7. **Clean Exit**:
   - `am force-stop com.ss.android.ugc.trill`
   - `input keyevent KEYCODE_HOME`

### 3. Tier 3: Home-Screen Widget Probe (Tertiary Fallback)
- For devices configured with the "Xóa bộ nhớ đệm" home screen widget shortcut:
  - Press HOME.
  - Probe widget position (default `810, 260`) with probe offsets `[(0, 0), (0, 120), (0, -120), (120, 0), (-120, 0)]`.

---

## Critical UI Distinctions & Pitfalls

- **Settings List vs Storage Subpage Classifier**:
  - The Settings list contains `"Bộ nhớ đệm & Dữ liệu di động"` and the `"Giải phóng dung lượng"` menu item, while ALSO displaying `"Cài đặt và quyền riêng tư"` / `"Settings and privacy"` as the top title.
  - `is_storage_screen(xml)` must explicitly return `False` if `"Cài đặt và quyền riêng tư"` / `"Settings and privacy"` is in the XML, avoiding false-positive early returns before the user taps into the storage subpage.
- **Cache vs Downloads Row Guard**:
  - The storage screen contains two distinct rows: "Bộ nhớ đệm" (Cache) and "Tải về" (Downloads: filters/stickers).
  - Always locate the vertical bounds `[y1, y2]` of the "Bộ nhớ đệm" row before finding and tapping the "Xóa" button inside `y1 <= btn_y <= y2`.
