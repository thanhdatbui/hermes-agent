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

### Case 10: Facebook Friends & Email Access Permission Dialog (Máy 50 Incident - 03/09/2026)
- **Faulty Pattern:**
  1. Rigid substring matching in `automation-core/benign_popup.py` requiring an exact single phrase and strictly requiring an `"OK"` label, failing on text variations or different button casing.
  2. Popup handler was missing from `BENIGN_POPUP_REGISTRY` in `benign_popup_registry.py`, preventing `find_matching_handler` from detecting and auto-dismissing it during swipe recovery, profile preflight, and account switcher guard.
  3. Missing rule in `automation_core.tiktok_popup.TIKTOK_POPUP_RULES`.
- **Failure Mechanism:** Dialog (*"Cho phép TikTok có quyền truy cập vào email và danh sách bạn bè trên Facebook của bạn?..."* with *"Không cho phép"* / *"OK"*) failed detection, classified as `manual-needed:popup` (`unexpected popup/dialog marker detected`), halting the session with a farm alert.
- **Fix Pattern:**
  1. **Multi-lingual & Variant Detection:** Support Vietnamese (*"truy cập vào email và danh sách bạn bè trên facebook"*, *"quyền truy cập vào email"*, *"danh sách bạn bè trên facebook"*) and English (*"access your email and facebook friends"*, *"facebook friends list"*), without strictly requiring the OK button.
  2. **Safe Deny-First Dismissal:** Detect and tap the deny node (*"Không cho phép"*, *"Từ chối"*, *"Don't allow"*, *"Deny"*, *"Hủy"*), with standard coordinate fallback `(deny_x, deny_y)` and `send_device_back_key`.
  3. **Centralized Registry Registration:** Register `facebook_contacts_email_permission` (Priority 92) in `BENIGN_POPUP_REGISTRY` and include in `allowlisted_drift_handlers` / profile preflight.
  4. **Core Rules Integration:** Add `facebook_contacts_email_permission_vi` & `facebook_contacts_email_permission_en` to `TIKTOK_POPUP_RULES`.

### Case 11: Video Editor & CapCut Template Creation Overlay Auto-Recovery (Máy 36 Incident - 04/09/2026)
- **Faulty Pattern:** Missing detector and dismisser in `classifier.py` and `benign_popup_registry.py` for Video Editor / CapCut template creation screens ("Sửa", "Âm thanh", "Văn bản", "Hiệu ứng", "Phép thuật", "Chú thích", "CapCut", "Mẫu CapCut").
- **Failure Mechanism:** When feed sessions or recovery flows encountered the video editor interface leftover from creation/draft flows, `classifier.py` classified the screen as `manual-needed:popup` with `unexpected popup/dialog marker detected`, aborting feed swipes and emitting farm alerts.
- **Fix Pattern:**
  1. **Dual Package & Multi-Tool Matcher:** Detect editor keywords ("âm thanh", "văn bản", "hiệu ứng", "phép thuật", "chú thích", "bộ lọc", "mẫu capcut", "timeline", "capcut", "video editor") or CapCut package (`com.lemon.lvoverseas`) with threshold (>=3 tools or >=2 tools + action keyword).
  2. **Negative Exclusions:** Strictly reject normal feed screens with bottom navigation dock (`Trang chủ` + `Hồ sơ`/`Hộp thư`), top feed tabs (`Dành cho bạn`/`Đang follow`), profile screens, and credential/verification inputs.
  3. **Safe Dismissal with Draft Modal Chaining:** Tap top-left Back/Close node or send `send_device_back_key`; if a draft continuation confirmation modal (*"Tiếp tục chỉnh sửa bài đăng này?"* / *"Lưu bản nháp"*) appears following Back, immediately invoke `_dismiss_draft_post_continuation` to clear the prompt cleanly.
  4. **Registry Registration:** Register `video_editor_overlay` with Priority 90 in `BENIGN_POPUP_REGISTRY` and map to `GENERIC_POPUP_SCREEN` in `classifier.py`.

### Case 12: Gmail Onboarding "Please add at least one email address" on Zero-Account Devices (Máy 76 Incident - 06/09/2026)
- **Faulty Pattern:** Unconditionally tapping `com.google.android.gm:id/action_done` ("ĐƯA TÔI TỚI GMAIL" / "TAKE ME TO GMAIL") in `dismiss_gmail_setup_addresses` on a freshly cleared Gmail app to reach the Inbox Home screen.
- **Failure Mechanism:** On clean/reset devices or newly provisioned phones where Google accounts count = 0 (e.g. after `pm clear`), Gmail cannot enter the Inbox without an existing account. Tapping "Đưa tôi tới Gmail" triggers an alert dialog: `android:id/message` = *"Vui lòng thêm ít nhất một địa chỉ email."* with `android:id/button1` = *"OK"*. Preflight fails to reach Gmail Home and aborts with `[BLOCKED][PRE_GMAIL][NOT_GMAIL_HOME]`.
- **Fix Pattern:**
  1. **Zero-Account Branching:** In account registration flows or when Google accounts count = 0, do NOT tap `action_done` ("Đưa tôi tới Gmail").
  2. **Direct Add Account Navigation:** Tap `com.google.android.gm:id/setup_addresses_add_address` ("Thêm địa chỉ email") -> select provider "Google" (`com.google.android.gm:id/account_setup_label`) to enter the Google account creation/login flow directly.
  3. **Alert Auto-Dismissal Fallback:** If dialog *"Vui lòng thêm ít nhất một địa chỉ email."* / *"Please add at least one email address"* appears, tap "OK" (`android:id/button1`), then fall back to tapping "Thêm địa chỉ email".

### Case 13: TikTok Account Switcher Row Tap Target & Settle Timing (Máy 79 Incident - 07/09/2026)
- **Faulty Pattern:**
  1. Trong `_find_account_switch_option`, khi row container full-width (`node.bounds[2] - node.bounds[0] >= 600`), script cố tìm inner `TextView` chứa username và ghi đè `best_bounds = inner.bounds` với giả định "tap trực tiếp lên username TextView thay vì khoảng trống bên phải".
  2. Trong `verify_and_switch_profile`, ngay sau khi tap switch row, script lập tức gọi `_navigate_profile_for_preflight(...)` dẫn đến tap Profile bottom tab `[972, 1857]`.
- **Failure Mechanism:**
  1. Trong UI XML của TikTok, row container là `android.widget.Button` (`id/l9b`, `clickable="true"`, toàn bộ chiều ngang `[0, y1][1080, y2]`, center x=540). Inner `TextView` (`id/mtx`, `text="<username>"`) có `clickable="false"`, bounds `[252, y1_inner][543, y2_inner]`, center x=397. Việc tap trúng `(397, y)` vào TextView không clickable khiến TikTok không nhận click listener trên container `Button id/l9b`.
  2. Việc tap Profile bottom tab `[972, 1857]` ngay sau khi tap switcher row khi sheet chưa kịp settle / animate đóng làm ngắt quãng luồng switch của TikTok (hoặc tap trúng nút "Thêm tài khoản" ở đáy nếu sheet còn mở), khiến tài khoản không chuyển đổi thành công.
- **Fix Pattern:**
  1. **Target Clickable Container:** Giữ nguyên `best_bounds` là bounds của container có `clickable="true"` (`node.bounds` từ `find_exact_account`, center x=540 hoặc avatar x~120). Tuyệt đối KHÔNG override vào inner non-clickable `TextView`.
  2. **Wait for Sheet Settle / Dismiss:** Sau khi tap account option trên Switcher, chờ và poll cho đến khi `is_switcher_open == False` (timeout 4-6s) để TikTok tự động reload profile và đóng bottom sheet.
  3. **No Redundant Profile Re-Navigation:** Vì switcher được mở từ Profile screen, sau khi sheet đóng thiết bị đã ở Profile tab, không tap lại `[972, 1857]`.

### Case 14: Cấm Tuyệt Đối `pm clear` Khi Sửa Lag / Cứu Kẹt Splash App TikTok (Sự Cố Admin Farm - 13/09/2026)
- **Faulty Pattern:** Dùng lệnh `pm clear com.ss.android.ugc.trill` để xử lý hiện tượng app TikTok bị kẹt màn hình đen `SplashActivity`, lag hoặc lỗi crash sau khi nâng cấp split APK.
- **Failure Mechanism:** Lệnh `pm clear` xóa toàn bộ thư mục `/data/data/com.ss.android.ugc.trill`, làm mất toàn bộ auth cookies, database token và session đăng nhập, đưa ứng dụng về màn onboarding `NewUserJourneyActivity` và văng toàn bộ tài khoản TikTok đang nuôi trên thiết bị.
- **Fix Pattern & Invariant:**
  1. **TUYỆT ĐỐI CẤM `pm clear`:** Cấm hoàn toàn việc chạy `pm clear` trên thiết bị farm trong mọi trường hợp (kể cả app lag, kẹt splash hay crash).
  2. **Nâng cấp an toàn (Keep Data):** Bổ sung Split APKs bắt buộc dùng:
     `adb install-multiple -r -d base.apk [splits...]` (cờ `-r` reinstall giữ nguyên toàn bộ data tài khoản).
  3. **Giải phóng treo Splash:** Kết thúc nâng cấp chỉ dùng `am force-stop` kết hợp `input keyevent 3` (HOME) để đưa máy về trạng thái an toàn. Nếu cần xóa cache, chỉ xóa thư mục cache an toàn hoặc reboot máy, tuyệt đối không đụng vào data.
