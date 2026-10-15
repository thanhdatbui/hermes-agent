# TikTok v47 Status Note Overlap and Pencil Entry Flow (2026-10-15)

## 1. Context and Problem Statement
On TikTok v47.0.3+ on Android devices (e.g. Samsung Galaxy S7 / G930F), the personal Profile layout introduces:
1. **Right-aligned Avatar Circle** at `[708,300][1080,636]`.
2. **Note Status Bubble ("Bạn có tin vui?", "Trà hay cà phê?")** at `[763,258][1037,465]` overlapping the upper half of the avatar circle.
3. **Story Creator "+" button ("Tạo một Nhật ký")** at `[931,499][1080,636]` overlapping the bottom-right corner of the avatar circle.

### The Pitfall
- When automated scripts attempt to tap the center or upper area of the avatar circle `(894, 468)` or `(900, 333)`, Android delivers the tap to the Note Status overlay, opening the "Tám chuyện nào" (Status Note composer) dialog instead of the avatar editor.
- Tapping the bottom-right corner opens the Story camera picker ("Thêm vào Nhật ký").
- Furthermore, the traditional rectangular "Sửa hồ sơ" button under the follower count is completely hidden in this layout.

## 2. The Reliable Resolution: Top-Left Pencil Entry
To bypass all overlapping bubbles and open Edit Profile reliably:
- **Pencil Icon Coordinates:** Tap `(75, 150)` (bounds `[126,96][228,204]`) in the top navigation bar.
- This invokes `ProfileEditActivity` ("Sửa hồ sơ") directly without touching the profile header.

### Step-by-Step Flow:
1. **Ensure Screen Awake:**
   - Execute `KEYCODE_WAKEUP` and `keyevent 82` before any UI actions. A sleeping screen produces empty/black screencaps (~12KB PNG).
2. **Open Edit Profile:**
   - Tap top-left pencil: `(75, 150)`, wait 2.5s.
   - Screen displays "Sửa hồ sơ".
3. **Trigger Avatar Picker:**
   - Tap "Thay đổi ảnh": `(540, 580)`, wait 2.0s.
   - Bottom sheet opens with: "Chụp ảnh", "Tải ảnh lên", "Xem ảnh".
   - Tap "Tải ảnh lên": `(540, 1637)`, wait 3.0s.
4. **Select Photo and Save:**
   - Photo picker opens ("Gần đây").
   - Tap top-left / first photo tile: `(215, 276)`, wait 2.0s.
   - Tap "Tiếp": `(1000, 1850)`, wait 3.5s.
   - Crop screen appears ("Cắt", "Lưu").
   - Tap "Lưu": `(792, 1794)`, wait 6.0s for image upload to complete.
5. **Return to Profile:**
   - Tap back button: `(84, 78)` or `keyevent 4`.

## 3. Ground Truth Verification Invariant
- **Never verify by exit code alone:** An adb tap script can return exit code 0 even if the screen was off or a popup intercepted the tap.
- **Physical Verification via Cascade Classifier (Face Detection):**
  ```python
  import cv2
  img = cv2.imread("profile_screencap.png")
  crop = img[300:636, 708:1080]  # Avatar circle bounds
  cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
  faces = cascade.detectMultiScale(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 1.1, 4)
  assert len(faces) >= 1, "Avatar crop does not contain human face!"
  ```
- This confirms that human portrait replacements (e.g. child/person) successfully replace stale cat/animal/stock avatars.
