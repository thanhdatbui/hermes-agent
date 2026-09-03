# UIAutomator & Popup Detection — Case Fixes & Anti-Pattern Catalog

## Key Lessons from Farm Incidents

### Case 1: False-Positive Camera Overlay on Profile Screen
- **Faulty Pattern:** Raw substring matching for generic keywords (e.g. `markers = ["10 phút", "60s", "15s", "ẢNH", "VĂN BẢN", "10m", "Photo", "Templates", "CAMERA"]` matching if count >= 2).
- **Failure Mechanism:** Profile tab naturally contains `"Ảnh hồ sơ"` (contains `ẢNH`/`Photo`) and `"Camera"` story button (contains `CAMERA`). This caused 100% of normal profile screens to trigger camera overlay detection, sending a `BACK` keyevent that kicked the app back to FYP, causing `profile verification mismatch` (`detected: null`), and locking 28 devices.
- **Fix Pattern:**
  1. **Negative Exclusions:** Check if screen contains Profile markers (`Đã follow`, `Follower`, `Sửa hồ sơ`, `Menu hồ sơ`...) or Bottom Navigation bar (`Trang chủ` + `Hộp thư` / `Hồ sơ`). If present, immediately return `False`.
  2. **Require Specific Shoot Modes:** Require specific duration/mode markers (`15s`, `60s`, `10 phút`, `templates`, `văn bản`) combined with camera controls (`lật`, `hẹn giờ`, `tốc độ`, `bộ lọc`), or explicit `shortvideo` / `record_layout` markers.
  3. **Distinguish Navigation Miss from Account Mismatch:** `detected: null` (profile not opened) is an ephemeral UI navigation issue, not an account mismatch.

### Case 2: Follow Friends Suggestion Popup
- **Faulty Pattern:** Substring matching `"Follow"` without context.
- **Failure Mechanism:** Matches video captions, recommendation chips, or creator follow buttons.
- **Fix Pattern:** Match exact phrase `"Follow bạn bè của bạn"`, `"Đồng bộ danh bạ"`, and tap `"Hủy"` / `"Để sau"`, excluding video caption resource-ids.

### Case 3: Location Permission Prompt
- **Faulty Pattern:** Pressing `BACK` to dismiss system location dialog.
- **Failure Mechanism:** Pressing `BACK` on some Android versions kills/backgrounds the parent TikTok activity.
- **Fix Pattern:** Find and tap the `"Hủy"` / `"Từ chối"` / `"Không cho phép"` node directly by bounds; fallback to `BACK` only if bounds missing, followed by foreground check.

### Case 4: In-App Browser / Webview
- **Faulty Pattern:** Repeated `BACK` loop.
- **Failure Mechanism:** Backs through web history and eventually exits TikTok.
- **Fix Pattern:** Find and tap the top `close_btn` / `iv_close` / `X` button.

### Case 5: Edit Profile Name Subpage
- **Faulty Pattern:** Typing via raw `adb shell input text`.
- **Failure Mechanism:** Drops accents or special characters, hangs keyboard.
- **Fix Pattern:** Use `AdbKeyboard` Base64 broadcast, dismiss keyboard, tap Save `[990, 138]` and Confirm `[750, 1175]`.

### Case 6: Watchdog Phase Misalignment
- **Faulty Pattern:** Watchdog reporting locked machines without pruning expired locks (>2h TTL).
- **Failure Mechanism:** Reaper runs at `0,15,30,45` and Watchdog runs at `0,15,30,45`, creating race/timing skew where locks at 124m are reported before reaper sweeps them.
- **Fix Pattern:** Watchdog auto-invokes reaper script before reading active locks; schedule offset by +1 minute (`1,16,31,46`).

### Case 7: False-Positive Comment Input Overlay on FYP Feed (29/08/2026 Incident)
- **Faulty Pattern:** Loose substring matching on `"bình luận"`, `"comment"`, `"viết bình luận"` matching normal video action button (`desc="Đọc hoặc viết bình luận. Bóc tem bình luận"`), combined with loose control matching on `"gửi"`, returning `True` without an active keyboard or focused input.
- **Failure Mechanism:** Normal FYP feed after swipe was classified as `manual-needed:popup` with reason `['comment input / story reply overlay marker present']`, halting multi-machine feed sessions and locking devices with `status: blocked`.
- **Fix Pattern:**
  1. **Negative Exclusions for FYP & Profile Navigation:** If screen contains bottom nav dock (`Trang chủ` + `Hồ sơ`/`Hộp thư`/`Cửa hàng`), top tabs (`Đề xuất`/`Bạn bè`/`Đã follow`), or standard profile elements, and neither keyboard nor focused input is present, return `False`.
  2. **Require Input / Keyboard Presence:** Must have focused TikTok `EditText` combined with active IME or comment input container (`comment_input_layout`, `comment_reply_et`...), or active system keyboard IME + TikTok `EditText`.
  3. **Tighten Keyword Matching:** Exclude generic words `"bình luận"`, `"comment"`, `"trả lời"`, `"reply"` and ignore `Button` nodes opening comments; match only explicit input placeholders (`"thêm bình luận"`, `"nhập bình luận"`, `"add a comment"`, `"để lại bình luận"`, `"say something"`).
  4. **Swipe Recovery XML Independence:** In multi-iteration stuck recovery (`_swipe_recovery_on_stuck`), iteration 2 must evaluate freshly recaptured XML (`current_attempt`), not the initial stale incident XML artifact, to avoid redundant `BACK` keyevents.

### Case 8: Negative Exclusions Scoping & Touch-Down Feed Swipe Shift (Sự cố Máy 68 ngày 30/08/2026)
- **Faulty Pattern:**
  1. Vòng lặp Negative Exclusions trong `detect_comment_input_overlay` quét trên toàn bộ cây XML `nodes` (bao gồm `com.android.systemui`), gặp notification của Google Play trên thanh trạng thái (*"Thông báo của Dịch vụ Google Play: Yêu cầu đăng nhập"*) chứa từ khóa `"đăng nhập"`.
  2. `_detect_camera_creation` (Priority 90 > 77) quét substring thô trên toàn bộ XML, khớp `"văn bản"` từ toolbar Samsung Keyboard (*"Hiển thị tiên đoán văn bản"*) và `"camera"` từ nút máy ảnh trên thanh nhắn tin nhanh (*"Mở máy ảnh"*, *"Văn bản camera"*).
  3. Điểm bắt đầu vuốt feed `BASE_SWIPE_START = (450, 1540)` (kèm jitter `1510..1570`) chạm trúng vùng tin nhắn nhanh / search pill ở đáy video (`y=1485..1563`), kích hoạt bàn phím ảo và gõ chuỗi `"55554"`.
- **Failure Mechanism:**
  - Detector comment overlay bị vô hiệu hóa bởi notification hệ thống $\rightarrow$ `classifier.py` trả về `unknown` $\rightarrow$ fail-closed `status: blocked` giữ hiện trường.
  - Ngón tay chạm trúng ô tin nhắn ở đáy mỗi lần vuốt feed nếu đặt toạ độ quá thấp (`y >= 1500`).
- **Fix Pattern:**
  1. **Strict TikTok Package Scoping:** Toàn bộ vòng lặp kiểm tra Negative Exclusions (`login_exclusions`, `otp_exclusions`, `security_exclusions`, `search_terms`, `profile_terms`) BẮT BUỘC chỉ quét trên `tiktok_nodes` (`com.ss.android.ugc.trill` / `com.zhiliaoapp.musically`), tuyệt đối KHÔNG duyệt qua `com.android.systemui`.
  2. **Camera Creation Guard:** Nếu `keyboard_detected == True`, `_detect_camera_creation` lập tức trả về `False` (viewfinder quay camera không bao giờ mở bàn phím ảo). Loại bỏ substring thô `"văn bản"` khỏi shoot mode markers đơn lẻ.
  3. **Safe Swipe Starting Zone:** Dời toạ độ bắt đầu vuốt feed từ `BASE_SWIPE_START = (450, 1540)` lên dải an toàn `BASE_SWIPE_START = (450, 1380)` (kết thúc tại `(450, 480)`). Vùng `y = 1380` nằm hoàn toàn trong mặt hiển thị video trống, cao hơn thanh mô tả/tin nhắn (`y >= 1485`) và nằm bên trái các nút Like/Comment (`x <= 500` vs `x >= 900`), triệt tiêu 100% khả năng chạm nhầm.

### Case 9: Account Logged Out Dialog Triage & Fail-Closed Alert Policy
- **Faulty / Risky Pattern:** Treating account logged-out popups (*"Trạng thái tài khoản: Tài khoản của bạn đã bị đăng xuất. Hãy thử đăng nhập lại."* / *"Account status: You've been logged out..."*) as generic dismissible popups by tapping "OK" or sending `BACK`.
- **Failure Mechanism:** Tapping "OK" dismisses the notice and routes the app to an unauthenticated landing or login screen. Subsequent feed/follow/upload automation continues running blindly without an active session, failing downstream assertions or burning rate limits.
- **Fix Pattern:**
  1. **Strict Detector Pair:** `detect_account_logged_out_popup` requires both title markers (`"trạng thái tài khoản"` / `"account status"`) AND body markers (`"đã bị đăng xuất"` / `"logged out"`).
  2. **Fail-Closed Classification:** Maps to `manual-needed:login` (confidence 0.99, `manual_needed=True`), terminating the flow without blind taps.
  3. **Farm Alert & Scene Hold:** Triggers `send_farm_machine_alert` with red banner screencap to Telegram (`-5373649734`) and retains device lock as `blocked` (TTL 90m) to preserve the incident scene for operator triage.
