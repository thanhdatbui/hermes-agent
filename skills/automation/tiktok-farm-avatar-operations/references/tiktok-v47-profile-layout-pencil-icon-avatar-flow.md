# TikTok v47.0.3 Profile Layout Navigation & Avatar Replacement Flow

## Context & Incident (15/10/2026)
On TikTok v47.0.3 accounts with active Note status ("Trà hay cà phê?", "Bạn có tin vui?") or Story buttons:
- The avatar bounds `[708,300][1080,636]` are covered by the Status Note overlay (`[777,258][1023,408]`) and Story (+) button (`[931,499][1080,636]`).
- Tapping the avatar directly opens the Note composer ("Tám chuyện nào") or Story camera instead of the avatar changer.
- The traditional rectangular "Sửa hồ sơ" button below follower counts is hidden under the new responsive profile layout.
- Attempting to tap blindly without verifying the resulting screen causes false completion reports where the avatar remains unchanged (e.g. still showing cat instead of target human portrait).

## Proven UI Navigation Path
1. **Direct Entry via Top-Left Pencil Icon:**
   - On the Profile screen, tap the pencil/edit icon in the top header bar at `(75, 150)` (bounds `[126,96][228,204]`, resource-id `com.ss.android.ugc.trill:id/zsj`).
   - This directly opens the **Sửa hồ sơ (Edit Profile)** Activity, bypassing all status notes and story bubbles.

2. **Avatar Selection Flow:**
   - In "Sửa hồ sơ", tap "Thay đổi ảnh" at `(540, 580)`.
   - Bottom sheet opens with 3 options: "Chụp ảnh", "Tải ảnh lên", "Xem ảnh".
   - Tap **"Tải ảnh lên"** at `(540, 1637)` (bounds `[0,1559][1080,1715]`).
   - In the MediaStore photo picker, tap the first tile at `(215, 276)`.
   - Tap "Tiếp" at bottom right `(1000, 1850)`.

3. **Crop & Upload:**
   - In the Crop screen, tap **"Lưu"** at center `(792, 1794)` (bounds `[552,1728][1032,1860]`).
   - Sleep 6.0s for the network upload to finish and return to "Sửa hồ sơ".
   - Tap back arrow at `(84, 78)` to return to Profile.

4. **Visual & Face-Detection Ground Truth Verification:**
   - Screencap the live profile: `dev.exec_out(["screencap", "-p"])`.
   - Crop avatar area `[708, 300, 1080, 636]`.
   - Run Haar cascade / OpenCV face detection to physically confirm a human face is present before declaring success. Never report success on exit code alone.
