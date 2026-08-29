# TỔNG HỢP CÁC CASE LỖI VẬN HÀNH FARM AUTOMATION & ANTI-PATTERNS

Tài liệu này tổng hợp toàn bộ các case lỗi thực tế trên hệ thống Farm TikTok (80-160 máy), nguyên nhân gốc rễ (Anti-Pattern) và giải pháp chuẩn hóa đã được kiểm chứng (Case Fix).

---

## MỤC LỤC
- [PHẦN 1: UI, POPUP, KEYBOARD & BÀN PHÍM ẢO](#phần-1-ui-popup-keyboard--bàn-phím-ảo)
  - [Case UI-01: False-Positive Camera Overlay trên trang Hồ sơ (Sự cố 28/08/2026)](#case-ui-01-false-positive-camera-overlay-trên-trang-hồ-sơ-sự-cố-28082026)
  - [Case UI-02: Popup "Follow bạn bè của bạn" / Follow Suggestion](#case-ui-02-popup-follow-bạn-bè-của-bạn--follow-suggestion)
  - [Case UI-03: Popup Xin quyền Vị trí (Location Permission Prompt)](#case-ui-03-popup-xin-quyền-vị-trí-location-permission-prompt)
  - [Case UI-04: Overlay Trình duyệt In-App (Webview / Landing Page)](#case-ui-04-overlay-trình-duyệt-in-app-webview--landing-page)
  - [Case UI-05: Màn hình Đổi Tên Hiển Thị Profile (Edit Name Subpage)](#case-ui-05-màn-hình-đổi-tên-hiển-thị-profile-edit-name-subpage)
  - [Case UI-06: Popup "Hoạt động không có sẵn" (Activity Unavailable)](#case-ui-06-popup-hoạt-động-không-có-sẵn-activity-unavailable)
  - [Case UI-07: Bàn phím ảo (IME) che khuất thanh điều hướng đáy](#case-ui-07-bàn-phím-ảo-ime-che-khuất-thanh-điều-hướng-đáy)
  - [Case UI-08: Gõ mật khẩu / chuỗi ký tự đặc biệt bằng ADB thô](#case-ui-08-gõ-mật-khẩu--chuỗi-ký-tự-đặc-biệt-bằng-adb-thô)
  - [Case POPUP-06: Chuỗi Popup Liên Hoàn (Add Phone ➔ Facebook/Contact Sync) & Khử Cờ Bàn Phím Ảo (Ghost IME)](#case-popup-06-chuỗi-popup-liên-hoàn-add-phone--facebookcontact-sync--khử-cờ-bàn-phím-ảo-ghost-ime)
  - [Case POPUP-07: Khung Nhập Bình Luận/Tin Nhắn Kèm Bàn Phím Ảo (Comment/Input Overlay) & Màn Hình Gợi Ý Tìm Kiếm (Search Landing)](#case-popup-07-khung-nhập-bình-luậntin-nhắn-kèm-bàn-phím-ảo-commentinput-overlay--màn-hình-gợi-ý-tìm-kiếm-search-landing)
  - [Case UI-11: Nhận diện Switcher Anchor Header & Khôi phục Drift Profile sau Back](#case-ui-11-nhận-diện-switcher-anchor-header--khôi-phục-drift-profile-sau-back)
  - [Case RECOVERY-04: Khôi phục 2 Tầng khi Văng Launcher (Relaunch ➔ Guarded Reboot & Chờ Gán VPN)](#case-recovery-04-khôi-phục-2-tầng-khi-văng-launcher-relaunch--guarded-reboot--chờ-gán-vpn)
- [PHẦN 2: CRON, SCHEDULER & WATCHDOG](#phần-2-cron-scheduler--watchdog)
  - [Case CRON-01: Lệch pha giữa Cron Dọn dẹp (Reaper) và Cron Thông báo (Watchdog)](#case-cron-01-lệch-pha-giữa-cron-dọn-dẹp-reaper-và-cron-thông-báo-watchdog)
  - [Case CRON-02: Runner Live Lease & Shift Isolation (Chống treo PID cũ cản trở ca sau)](#case-cron-02-runner-live-lease--shift-isolation-chống-treo-pid-cũ-cản-trở-ca-sau)
  - [Case CRON-03: Chống Double Spawn khi Runner hoàn tất giữa chừng](#case-cron-03-chống-double-spawn-khi-runner-hoàn-tất-giữa-chừng)
  - [Case COHORT-03: Cohort Target Validation khi Thiếu Field Tuỳ Chọn (missing:tik)](#case-cohort-03-cohort-target-validation-khi-thiếu-field-tuỳ-chọn-missingtik)
  - [Case UPLOAD-01: Mở rộng Hạn Mức Tải & Hàng Đợi Upload Video Cuối Ca (Phiên 3)](#case-upload-01-mở-rộng-hạn-mức-tải--hàng-đợi-upload-video-cuối-ca-phiên-3)
- [PHẦN 3: FILE SYNC & DATA INTEGRITY](#phần-3-file-sync--data-integrity)
  - [Case SYNC-01: Race Condition khi ghi file taikhoan_run_safe trên OneDrive 2 PC](#case-sync-01-race-condition-khi-ghi-file-taikhoan_run_safe-trên-onedrive-2-pc)
  - [Case SYNC-02: Parse Device ID / Serial bị dính định dạng Ngày tháng trong Excel](#case-sync-02-parse-device-id--serial-bị-dính-định-dạng-ngày-tháng-trong-excel)
  - [Case SYNC-03: Daily Cooldowns File Lock (.flock) và cơ chế Check-and-Reserve UUID](#case-sync-03-daily-cooldowns-file-lock-flock-và-cơ-chế-check-and-reserve-uuid)
  - [Case SYNC-04: Đồng bộ 1-chiều Master DAT sang Tik1..Tik6.xlsx khi tài khoản bị xóa / để trống](#case-sync-04-đồng-bộ-1-chiều-master-dat-sang-tik1tik6xlsx-khi-tài-khoản-bị-xóa--để-trống)
- [PHẦN 4: DEVICE LOCK & MULTI-MACHINE SAFETY](#phần-4-device-lock--multi-machine-safety)
  - [Case LOCK-01: Giữ nguyên hiện trường Lock Blocked đủ TTL 2h (Cấm tự tiện Unlock vội)](#case-lock-01-giữ-nguyên-hiện-trường-lock-blocked-đủ-ttl-2h-cấm-tự-tiện-unlock-vội)
  - [Case LOCK-02: Destructive Actions Denylist (Cấm kill-server / pm clear làm sập farm)](#case-lock-02-destructive-actions-denylist-cấm-kill-server--pm-clear-làm-sập-farm)
  - [Case LOCK-03: Proxy sập ➔ Fail-Closed (Cấm chạy Direct IP)](#case-lock-03-proxy-sập--fail-closed-cấm-chạy-direct-ip)
  - [Case LOCK-04: Batch Reservation Lock Fault Isolation (Cô lập lỗi Lock/Guard từng máy, chống Crash toàn bộ Farm)](#case-lock-04-batch-reservation-lock-fault-isolation-cô-lập-lỗi-lockguard-từng-máy-chống-crash-toàn-bộ-farm)
  - [Case LOCK-05: Kế thừa Device Lock cho Subprocess Follow Hook (--skip-identity-verify)](#case-lock-05-kế-thừa-device-lock-cho-subprocess-follow-hook---skip-identity-verify)

---

## PHẦN 1: UI, POPUP, KEYBOARD & BÀN PHÍM ẢO

### Case UI-01: False-Positive Camera Overlay trên trang Hồ sơ (Sự cố 28/08/2026)
- **Vị trí áp dụng:** `python_runner/flows/benign_popup_registry.py` (`_detect_camera_creation`), `python_runner/flows/feed_swipe_smoke.py` (`_verify_profile_after_session`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Quét substring từ khóa thô trên toàn bộ XML dump:
  ```python
  # ❌ SAI LẦM:
  markers = ["10 phút", "60s", "15s", "ẢNH", "VĂN BẢN", "10m", "Photo", "Templates", "CAMERA"]
  combined = ((xml_content or "") + " " + (ocr_text or "")).casefold()
  match_count = sum(1 for marker in markers if marker.casefold() in combined)
  return match_count >= 2
  ```
  Trang Hồ sơ chuẩn luôn có `content-desc="Ảnh hồ sơ"` và nút `content-desc="Camera"` ➔ `match_count >= 2` luôn đúng. Script gửi phím BACK để "tắt camera" làm văng khỏi Profile về lại FYP, không đọc được username (`detected: null`), báo lỗi giả `profile account mismatch` và kích hoạt `status: blocked` trên 28 máy.
- **Giải pháp chuẩn (Case Fix):**
  1. **Negative Exclusions:** Kiểm tra loại trừ nếu màn hình có các trường của Profile (`Đã follow`, `Follower`, `Sửa hồ sơ`, `Menu hồ sơ`...) hoặc thanh điều hướng đáy FYP (`Trang chủ` + `Hộp thư` / `Hồ sơ`) ➔ Trả về `False` ngay lập tức.
  2. **Yêu cầu cụm từ chế độ quay đặc thù:** Tối thiểu 2 chế độ quay (`15s`, `60s`, `10 phút`, `10m`, `templates`, `văn bản`, `tạo`) HOẶC 1 chế độ quay + 1 công cụ camera (`lật`, `hẹn giờ`, `tốc độ`, `bộ lọc`, `thêm âm thanh`).
  3. **Độc lập lỗi:** Không đọc được username do bấm trượt navigation (`detected: null`) KHÔNG ĐƯỢC coi là lỗi tài khoản (`account mismatch`).

---

### Case UI-02: Popup "Follow bạn bè của bạn" / Follow Suggestion
- **Vị trí áp dụng:** `python_runner/flows/benign_popup.py` (`detect_follow_friends_suggestion_popup`, `dismiss_follow_friends_suggestion_popup`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Tìm text `"Follow"` chung chung ➔ Khớp vào nút Follow của video đang phát hoặc caption creator, gây tap nhầm follow ngoài ý muốn làm đứt chuỗi lướt feed.
- **Giải pháp chuẩn (Case Fix):**
  1. Khớp chính xác cụm tiêu đề: `"Follow bạn bè của bạn"`, `"Đồng bộ danh bạ"`, `"Tìm bạn bè"`.
  2. Nút bấm dismiss ưu tiên: `"Hủy"`, `"Để sau"`, `"Không phải bây giờ"`, icon `"close"`.
  3. Bỏ qua nếu từ khóa nằm trong node caption video (`@resource-id="...desc"` hoặc `...title`).

---

### Case UI-03: Popup Xin quyền Vị trí (Location Permission Prompt)
- **Vị trí áp dụng:** `python_runner/flows/benign_popup_registry.py` (`_detect_location_prompt`, `_dismiss_location_prompt`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Bấm phím BACK để tắt dialog vị trí ➔ Trên một số bản Android/TikTok, bấm BACK khi permission dialog mở sẽ đóng luôn Activity chính của TikTok, làm app rơi vào background.
- **Giải pháp chuẩn (Case Fix):**
  1. Tìm Node nút `"Hủy"`, `"Không cho phép"`, `"Từ chối"`, `"Trong khi dùng ứng dụng"`, `"Chỉ lần này"` qua XML.
  2. Tap trực tiếp vào tọa độ/bounds của nút `"Hủy"` / `"Từ chối"`.
  3. Chỉ fallback BACK khi không tìm thấy bounds và sau đó phải kiểm tra lại `get_focused_activity`.

---

### Case UI-04: Overlay Trình duyệt In-App (Webview / Landing Page)
- **Vị trí áp dụng:** `python_runner/flows/benign_popup_registry.py` (`_detect_inapp_browser`, `_dismiss_inapp_browser`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Tap nhầm CTA quảng cáo mở Webview, script liên tục gửi BACK làm back xuyên qua web history rồi văng ra Launcher.
- **Giải pháp chuẩn (Case Fix):**
  1. Nhận diện Webview qua `class="android.webkit.WebView"` hoặc resource-id chứa `cross_btn`, `close_btn`, `btn_close`, `iv_close`.
  2. Bấm nút Đóng (`X`) ở góc trên màn hình để đóng Webview dứt điểm.

---

### Case UI-05: Màn hình Đổi Tên Hiển Thị Profile (Edit Name Subpage)
- **Vị trí áp dụng:** `python_runner/flows/benign_popup_registry.py` (`_detect_edit_name`, `_dismiss_edit_name`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Nick mới mở Hồ sơ bị chặn bởi màn hình "Thêm tên bạn mong muốn", script không xử lý dẫn tới kẹt verify.
- **Giải pháp chuẩn (Case Fix):**
  1. Nhận diện chuỗi `"Thêm tên bạn mong muốn"` hoặc `"Đổi tên một lần mỗi 7 ngày"`.
  2. Sinh tên tiếng Việt tự nhiên qua `make_tiktok_name(email)`.
  3. Nhập Base64 qua `AdbKeyboard`, ẩn bàn phím, tap Lưu `[990, 138]` và Xác nhận `[750, 1175]`.

---

### Case UI-06: Popup "Hoạt động không có sẵn" (Activity Unavailable)
- **Vị trí áp dụng:** `python_runner/flows/benign_popup_registry.py` (`_detect_activity_unavailable`, `_dismiss_activity_unavailable`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Hiện dialog chuyển sang tài khoản ban đầu làm mờ màn hình và chặn swipe.
- **Giải pháp chuẩn (Case Fix):**
  Nhận diện tiêu đề `"Hoạt động không có sẵn"` + nội dung `"chuyển sang tài khoản ban đầu"`, gửi lệnh BACK hoặc tap ngoài dialog để giải phóng màn hình mờ.

---

### Case UI-07: Bàn phím ảo (IME) che khuất thanh điều hướng đáy
- **Vị trí áp dụng:** `python_runner/flows/feed_swipe_smoke.py`, `core/keyboard.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Bàn phím ảo nổi che khuất vùng đáy `[0, 1794][1080, 1920]`, tap Profile chạm trúng phím Enter/Dấu cách.
- **Giải pháp chuẩn (Case Fix):**
  Trước khi tap điều hướng đáy, gọi `cleanup_keyboard_before_nav` (gửi `input keyevent 111` / Escape) và kiểm tra `dumpsys input_method` đảm bảo `mInputShown=false`.

---

### Case UI-08: Gõ mật khẩu / chuỗi ký tự đặc biệt bằng ADB thô
- **Vị trí áp dụng:** Toàn bộ runner login/register/2FA.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Dùng `adb shell input text "P@ss!"` bị shell nuốt ký tự đặc biệt (`@`, `!`, `&`, `#`, `$`, `%`...), gây lỗi "Sai mật khẩu" giả tạo (sự cố m76).
- **Giải pháp chuẩn (Case Fix):**
  BẮT BUỘC dùng `AdbKeyboard` qua broadcast Base64:
  `adb shell am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <base64>`

---

### Case POPUP-06: Chuỗi Popup Liên Hoàn (Add Phone ➔ Facebook/Contact Sync) & Khử Cờ Bàn Phím Ảo (Ghost IME)
- **Vị trí áp dụng:** `automation_core/keyboard.py`, `python_runner/flows/benign_popup.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  1. Sau khi đóng popup Thêm số điện thoại (Add Phone), daemon bàn phím Samsung (`com.sec.android.inputmethod` trên Galaxy S7) trong `dumpsys input_method` vẫn lưu cờ cũ `mInputShown=true` / `mShowRequested=true`.
  2. Màn hình ngay sau đó lập tức nhảy lên popup thứ 2 (Facebook contacts/email permission `manual-needed:popup`).
  3. Logic dọn bàn phím kiểm tra màn hình tiếp theo bằng `_is_known_tiktok_screen_after_add_phone`. Do thiếu `manual-needed:popup` trong allowlist, fallback từ chối xử lý và báo lỗi `keyboard remained visible after dismiss attempt`, chặn đứng flow trước khi Registry kịp bấm *Không cho phép*.
- **Giải pháp chuẩn (Case Fix):**
  1. **Đưa `com.sec.android.inputmethod` vào `KNOWN_KEYBOARD_PACKAGES`:** Nhận diện đúng gói bàn phím Samsung chuẩn.
  2. **XML là bằng chứng khẳng định (Positive Detection) & Window Manager bit `0x2` làm chuẩn:** Trong `detect_keyboard_state`, cây XML chỉ dùng để khẳng định có bàn phím ngay lập tức khi phát hiện package bàn phím; khi XML không có node bàn phím, fallback xuống `dumpsys input_method` và đọc bit 1 (`0x2 = IME_VISIBLE`) của trường `mImeWindowVis` từ Window Manager. Khi `mImeWindowVis=0x0` hoặc `0x1` hoặc `mInputViewShown=false`, xác định dứt khoát `visible=False`, triệt tiêu cờ stale `mInputShown=true` của Samsung Keypad.
  3. **Xử lý Popup Quyền Facebook (Contacts/Email Permission) Chuẩn Hoá Toàn Diện (Cả Chained lẫn Standalone):** Popup đồng bộ danh bạ/email Facebook (`detect_facebook_contacts_email_permission_dialog`) có thể xuất hiện nối tiếp sau Add Phone hoặc xuất hiện độc lập (standalone) tại màn hình Profile/FYP. Thay vì ép buộc token chuỗi gây chặn các popup độc lập, detector xác thực dựa trên cấu trúc XML chính xác (nội dung câu hỏi quyền email + bạn bè Facebook và đầy đủ cặp nút OK / Không cho phép) và tự động dismiss an toàn bằng action `dismiss_deny_button` (*Không cho phép*).
  4. **Mở rộng màn hình hợp lệ sau Add Phone:** Bổ sung `GENERIC_POPUP_SCREEN` (`manual-needed:popup`), `PACKAGEINSTALLER_DIALOG_SCREEN` và các benign popup vào `_KNOWN_TIKTOK_SCREENS_AFTER_ADD_PHONE` và `_blocked_after_close_reason` để flow chuyển tiếp mượt sang Registry giải quyết tiếp popup thứ 2.

---

### Case POPUP-07: Khung Nhập Bình Luận/Tin Nhắn Kèm Bàn Phím Ảo (Comment/Input Overlay) & Màn Hình Gợi Ý Tìm Kiếm (Search Landing)
- **Vị trí áp dụng:** `python_runner/core/classifier.py`, `python_runner/flows/benign_popup_registry.py`, `python_runner/flows/feed_swipe_smoke.py` (`_swipe_recovery_on_stuck`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  1. Khi lướt Feed, thao tác chạm hoặc vuốt ở nửa dưới màn hình vô tình chạm trúng khung bình luận/chat, làm bàn phím ảo (`com.sec.android.inputmethod` / `com.samsung.android.honeyboard`) bật lên che khuất thanh điều hướng đáy.
  2. Các lệnh vuốt tiếp theo (`swipe` hoặc `_swipe_recovery_on_stuck` ở `y=1540..1600`) chạm đè lên bàn phím ảo, bị chuyển thành các lần gõ phím liên tiếp vào `EditText` (ví dụ gõ chuỗi `"454"`) thay vì cuộn video.
  3. `classifier.py` không nhận diện được màn hình do mất thanh điều hướng Home/Profile, `_probe_gemphonefarm_blind_popups` không có selector đóng ô nhập, dẫn tới fail-closed `unknown TikTok state; swipe recovery (2 swipes) still stuck`.
- **Giải pháp chuẩn (Case Fix):**
  1. **Đăng ký `detect_search_landing_page` & `_dismiss_search_landing` (Priority 84):**
     - Đặt mức ưu tiên cao hơn comment overlay (Priority 84 > 77) để xử lý dứt điểm màn hình tìm kiếm trước.
     - Nhận diện các section keywords (`bạn có thể thích`, `tìm kiếm gần đây`, `gợi ý tìm kiếm`, `nội dung tìm kiếm thịnh hành`) kết hợp `EditText`/nút tìm kiếm.
     - Dismisser ưu tiên tìm và tap nút Back ngữ nghĩa (node ở góc trên bên trái `bounds=[0..200, 0..300]` có `content-desc`/`text` trong `{"quay lại", "back", "trở lại", "←", "<"}` hoặc resource-id chứa `back`/`close`), fallback gửi phím `BACK`.
  2. **Đăng ký `detect_comment_input_overlay` & `_dismiss_comment_input` (Priority 77):**
     - **Negative Exclusions:** Bắt buộc loại trừ form Login (`login_email`, `btn_login`), OTP (`otp_input`, `mã xác minh`), CAPTCHA (`puzzle`, `sec_check`), Edit name (`thêm tên bạn mong muốn`), Profile chuẩn (`Đã follow`, `Follower`, `Sửa hồ sơ`...), và FYP feed chuẩn (có đủ thanh điều hướng Home/Profile/Inbox/Shop hoặc tab Đề xuất/Bạn bè/Đã follow khi bàn phím KHÔNG mở và KHÔNG có EditText focused).
     - **Positive Detection (bắt buộc gắn với Input/Keyboard):** Match khi (1) có `EditText` focused trong TikTok kèm bàn phím ảo hiển thị (`honeyboard`, `inputmethod`, `latin`, `swiftkey`, `gboard`) hoặc cụm điều khiển gửi/nhãn dán; HOẶC (2) có bàn phím ảo hiển thị kết hợp `EditText` / comment input resource-id / hint text; HOẶC (3) có layout khung nhập bình luận cụ thể (`comment_input_layout`, `comment_panel`, `comment_drawer`) kết hợp `EditText`.
     - **Dismisser & Hậu kiểm (Post-condition):** Gửi 1 phím `BACK` để hạ bàn phím ảo; sau 0.8s nếu hierarchy dump lại vẫn còn overlay (`detect_comment_input_overlay == True`) thì gửi tiếp phím `BACK` thứ 2 để thoát hoàn toàn focus ô nhập về Feed.
  3. **Nâng cấp `_swipe_recovery_on_stuck`:**
     - Trước khi swipe: Kiểm tra `find_matching_handler` trong Registry và `detect_keyboard_state`; nếu bàn phím đang mở thì gửi `BACK` hạ bàn phím trước, đồng thời dời tọa độ bắt đầu vuốt từ `y=1600` lên `y=1400` để không chạm trúng bàn phím.
     - Hậu kiểm sau mỗi lượt swipe recovery: Recapture UI; nếu màn hình về feed hợp lệ (`for-you`, `following`, `friends`) thì khôi phục `status=success`; nếu màn hình xuất hiện popup phụ thì cho phép Registry xử lý tiếp. Nếu sau 2 lượt vẫn kẹt ở trạng thái `unknown` thì dừng an toàn dạng fail-closed giữ nguyên hiện trường.

---

### Case UI-11: Nhận diện Switcher Anchor Header & Khôi phục Drift Profile sau Back
- **Vị trí áp dụng:** `python_runner/flows/feed_swipe_smoke.py` (`_find_sticky_profile_header`, `_capture_profile_switcher_xml_with_add_phone_guard`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  1. `_find_sticky_profile_header` lấy nhầm `display_name_element` ở thân trang (`center_y > 400px`) do thiếu điều kiện giới hạn vùng header (`center[1] <= 320`). Bấm vào thân trang không mở bottom sheet đổi tài khoản.
  2. Khi switcher không mở, recovery gửi phím `BACK` làm TikTok lùi về tab Bạn bè / Khám phá. Flow sau đó không nhận diện đã rời khỏi Profile mà tiếp tục re-tap tọa độ cũ lên tab Bạn bè ➔ báo lỗi giả `profile screen remained after switch-anchor tap`.
- **Giải pháp chuẩn (Case Fix):**
  1. Giới hạn sticky header strictly ở vùng header trên cùng (`center[1] <= 320`), buộc flow thực hiện cuộn nhẹ (`_profile_scroll`) để hiện sticky header chính giữa trước khi tap.
  2. Trong recovery: Kiểm tra nếu bị drift khỏi Profile, tự động navigate lại Profile root (`_navigate_profile_for_preflight`), cuộn nhẹ để hiện sticky header và resolve lại anchor mới trước khi retry.

---

### Case RECOVERY-04: Khôi phục 2 Tầng khi Văng Launcher (Relaunch ➔ Guarded Reboot & Chờ Gán VPN)
- **Vị trí áp dụng:** `python_runner/flows/feed_swipe_smoke.py` (`_recover_post_swipe_launcher_focus`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Khi TikTok bị crash hoặc bị hệ điều hành đóng ngầm do cạn kiệt RAM (Low Memory Killer) và rơi về màn hình chính (Launcher), cơ chế recovery cũ chỉ gọi `force_stop_and_relaunch_tiktok` 1 lần duy nhất. Do RAM chưa được giải phóng hoặc app tiếp tục crash ngay sau khi mở, nhịp recapture không xác nhận được Feed, dẫn tới dừng phiên `FINAL_BLOCKED` giữ hiện trường mà không tận dụng cơ chế khởi động lại máy.
- **Giải pháp chuẩn (Case Fix):**
  1. **Khôi phục 2 tầng tuần tự:** Tầng 1 thử `force_stop_and_relaunch_tiktok` (nhanh, nhẹ, không mất kết nối mạng).
  2. **Fallback sang Guarded Reboot:** Nếu Tầng 1 không xác nhận được Feed (`not recovered`), tự động chuyển sang Tầng 2: Kích hoạt `reboot_and_restore` từ `automation-core`.
  3. **Bắt buộc chờ gán và kiểm tra VPN sau Reboot:** Sử dụng callback `wait_for_proxy_ready` kết hợp verifier `require_vichanger_connected` để đảm bảo proxy-watcher đã kết nối lại VPN an toàn 100% trước khi mở TikTok, ngăn chặn tuyệt đối rò rỉ Direct IP.
  4. **Khởi động lại TikTok & Recapture Feed:** Sau khi VPN đã kết nối, mở TikTok với delay ổn định 10s và recapture UI xác nhận màn hình Feed trước khi tiếp tục lướt.
  5. **Giới hạn an toàn (Bounded Recovery):** Cờ `_launcher_reboot_attempted` giới hạn tối đa 1 lần reboot trên mỗi thiết bị trong một phiên chạy để tránh vòng lặp bất tận.

---

## PHẦN 2: CRON, SCHEDULER & WATCHDOG

### Case CRON-01: Lệch pha giữa Cron Dọn dẹp (Reaper) và Cron Thông báo (Watchdog)
- **Vị trí áp dụng:** `deploy/hermes-home/scripts/watch_device_locks.py`, `scripts/reap-dead-owner-locks.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Reaper chạy định kỳ `XX:00, XX:15, XX:30, XX:45`. Watchdog chạy ở `XX:11, XX:26, XX:41, XX:56`. Lock vừa chạm 120 phút ở `XX:52` thì Watchdog quét thấy lúc `XX:56` và bắn cảnh báo Telegram `⚠️ QUÁ HẠN > 2H`, trong khi Reaper đến `XX:00` mới đến lịch dọn ➔ Tạo ra cảnh báo rác "Tại sao quá 2h đéo tự unlock".
- **Giải pháp chuẩn (Case Fix):**
  1. **Preflight Auto-Reap:** Ngay đầu hàm `run_watchdog()` của watchdog script, chủ động gọi chạy `reap-dead-owner-locks.py` để dọn sạch toàn bộ lock hết hạn trước khi scan danh sách báo cáo.
  2. **Đồng bộ lịch Cron:** Xếp lịch Watchdog chạy sau Reaper 1 phút (`1,16,31,46 * * * *`).

---

### Case CRON-02: Runner Live Lease & Shift Isolation (Chống treo PID cũ cản trở ca sau)
- **Vị trí áp dụng:** `scripts/tiktok_runner.py` (`_spawn_live`, `_lease_alive`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Tiến trình feed runner của ca trước bị treo hoặc chạy quá 90 phút nhưng file lease vẫn tồn tại. Khi ca mới bắt đầu, runner thấy lease cũ còn sống nên bỏ qua không spawn ca mới.
- **Giải pháp chuẩn (Case Fix):**
  1. **Hard Expiry & Timeout Guard:** Giới hạn max runtime của 1 batch feed là 90 phút (5400s). Nếu vượt quá, tự động kill PID stale qua handle an toàn và xóa lease.
  2. **Shift Isolation:** Khi cohort_id của ca mới khác với cohort_id trong lease hiện tại, runner tự động thu hồi tiến trình ca cũ và nhường quyền cho ca mới.

---

### Case CRON-03: Chống Double Spawn khi Runner hoàn tất giữa chừng
- **Vị trí áp dụng:** `scripts/tiktok_runner.py` (`_terminal_cohort_machines`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Cron tick 15 phút gọi lại khi một số máy đã hoàn tất phiên và thoát, runner thấy thiếu máy lại spawn lại từ đầu, làm các máy đã chạy bị lướt đúp 2 lần trong 1 ca.
- **Giải pháp chuẩn (Case Fix):**
  Quét publications terminal (`collect_publications`) của cohort hiện tại. Lọc bỏ các máy đã có kết quả terminal, chỉ spawn những máy còn thiếu. Nếu tất cả máy đã terminal ➔ Thu hồi lease và không spawn lại.

---

### Case COHORT-03: Cohort Target Validation khi Thiếu Field Tuỳ Chọn (missing:tik)
- **Vị trí áp dụng:** `python_runner/flows/multi_machine_feed_session.py` (`_apply_cohort_identity`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Hàm `_apply_cohort_identity` bắt buộc `tik` phải có trong `expected` (`if "tik" not in expected: mismatches.append("missing:tik")`). Khi manifest phân bổ ca chạy (ví dụ Row 4) không khai báo key `tik`, toàn bộ máy trong ca đều bị đánh dấu `cohort target identity mismatch: missing:tik`, sinh ra lock `blocked` giả và làm tê liệt toàn bộ ca chạy.
- **Giải pháp chuẩn (Case Fix):**
  Chỉ đối soát `tik` khi `expected` có khai báo key `"tik"` (`if "tik" in expected: ...`).

---

### Case UPLOAD-01: Mở rộng Hạn Mức Tải & Hàng Đợi Upload Video Cuối Ca (Phiên 3)
- **Vị trí áp dụng:** `python_runner/flows/multi_machine_feed_session.py`, `feed_session_watchdog.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Ở Phiên 3, 60+ máy cùng hoàn thành lướt feed và đổ dồn vào hook upload. Với `DEFAULT_UPLOAD_MAX_CONCURRENCY = 16` và `timeout = 1200s (20 phút)`, các máy xếp hàng sau bị chạm trần hard deadline của worker (`upload-timeout`), không hoàn thành upload video.
- **Giải pháp chuẩn (Case Fix):**
  Nâng concurrency upload lên 20 workers (`DEFAULT_UPLOAD_MAX_CONCURRENCY = 20`), nâng timeout upload lên 45 phút (`DEFAULT_UPLOAD_HOOK_TIMEOUT_SECONDS = 2700.0`), nới rộng hard deadline worker lên 100 phút (6000s) cho Phiên 3, và nới rộng khung giờ trên watchdog.

---

## PHẦN 3: FILE SYNC & DATA INTEGRITY

### Case SYNC-01: Race Condition khi ghi file taikhoan_run_safe trên OneDrive 2 PC
- **Vị trí áp dụng:** `scripts/hermes_taikhoan_sync_cron.py`, `automation_core/workbook_lock.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  2 PC (Kibe và Admin) cùng mở và ghi trực tiếp vào file Excel trên OneDrive, tạo ra file xung đột `taikhoan_run_safe-DESKTOP-XXX.xlsx` và làm mất dữ liệu cập nhật trạng thái nick.
- **Giải pháp chuẩn (Case Fix):**
  1. **Single Writer Protocol:** Chỉ PC được chỉ định (hoặc tiến trình giữ workbook lock có TTL) mới được ghi.
  2. **Atomic Temp File + Replace:** Ghi ra file `.tmp` trước, sau đó dùng `os.replace` nguyên tử để cập nhật file chính thức.

---

### Case SYNC-02: Parse Device ID / Serial bị dính định dạng Ngày tháng trong Excel
- **Vị trí áp dụng:** `scripts/hermes_taikhoan_sync_cron.py`, `python_runner/tools/machine_mapping.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Cột Device ID trong Excel có các giá trị dạng `26/08/2026` do người dùng ghi chú ngày. Script đọc nhầm giá trị này làm Serial thiết bị, gây lỗi không tìm thấy thiết bị ADB.
- **Giải pháp chuẩn (Case Fix):**
  Kiểm tra Regex định dạng Serial chuẩn (chuỗi hex/alphanumeric hợp lệ, độ dài chuẩn, không chứa ký tự `/`, `-`, `:` của ngày tháng). Nếu dính text ngày ➔ Tự động tra cứu fallback sang `config-machine-XX.yaml` hoặc mapping canonical.

---

### Case SYNC-03: Daily Cooldowns File Lock (.flock) và cơ chế Check-and-Reserve UUID
- **Vị trí áp dụng:** `core/target_lock.py`, `scripts/night_chain_reg_pipeline.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Nhiều worker chạy song song cùng đọc kho mail dư và cùng gán 1 email cho 2 máy khác nhau, gây trùng lặp và hỏng tài khoản reg.
- **Giải pháp chuẩn (Case Fix):**
  Dùng cơ chế **Check-and-Reserve có UUID Token** kết hợp file lock độc quyền (`.reg_daily_cooldowns.json.flock`). Worker phải reserve thành công trong lock mới được cấp phát target.

---

### Case SYNC-04: Đồng bộ 1-chiều Master DAT sang Tik1..Tik6.xlsx khi tài khoản bị xóa / để trống
- **Vị trí áp dụng:** `scripts/sync-tik-workbooks.py` trong repo `tiktok-luot nuoi acc`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  1. Khi người dùng xóa tài khoản die/bị ban khỏi bảng master `taikhoan_dat_v2_updated .xlsx` (cột ID để trống `None`), script `sync-tik-workbooks.py` chỉ ghi đè khi master có nick mới hợp lệ (`if target_id and cur_val != target_id`), và chỉ xóa ô ở file con TikN nếu ô đó chứa placeholder rác cụ thể (`none`, `null`, `ghjfghj`, link `http`). Do đó, username cũ đã bị xóa khỏi master vẫn bị giữ lại trong `Tik1..Tik5.xlsx`.
  2. Bảng mapping `TIK_SLOT_MAP` bị thiếu slot `Tik5.xlsx` và `Tik6.xlsx`.
  3. Trong thư viện `openpyxl`, việc gọi `ws.cell(r, c, None)` không xóa giá trị ô hiện hữu, và nếu ô có chứa Hyperlink đối tượng thì chỉ gán `cell.value` sẽ không xóa sạch metadata.
- **Giải pháp chuẩn (Case Fix):**
  1. Mở rộng `TIK_SLOT_MAP` hỗ trợ đủ các file từ `Tik1.xlsx` đến `Tik6.xlsx` (slot 1..6).
  2. Đồng bộ 1-chiều tuyệt đối: Bất kể ô cũ chứa giá trị gì, nếu `raw_cur != (target_id if target_id else "")`, thực hiện cập nhật `cell = ws_tik.cell(r, id_col); cell.value = target_id if target_id else None`.
  3. Xóa sạch hyperlink khi nick bị xóa (`if not target_id: cell.hyperlink = None`) để tránh lưu vết link rác.
  4. Tự động đồng bộ cột `Kiểm Tra Dữ Liệu`: Cập nhật thành `"OK"` khi có ID và `"MISSING_ID"` khi ID bị trống, bảo toàn nguyên vẹn 100% cột `Folder Video` và `Video Đã Đăng`.

---

## PHẦN 4: DEVICE LOCK & MULTI-MACHINE SAFETY

### Case LOCK-01: Giữ nguyên hiện trường Lock Blocked đủ TTL 2h (Cấm tự tiện Unlock vội)
- **Vị trí áp dụng:** `automation_core/device_lock.py`, `scripts/reap-dead-owner-locks.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Khi máy bị lỗi (ví dụ OTP timeout, camera popup, proxy die), script tự tiện xóa lock hoặc unlock ngay lập tức. Runner đợt sau vào chạy đè lên hiện trường, làm mất sạch dấu vết UI XML và screenshot để debug.
- **Giải pháp chuẩn (Case Fix):**
  Trạng thái `blocked` **BẮT BUỘC giữ nguyên hiện trường** với TTL tối đa 2 giờ (7200s). Trong 2 giờ này, các runner khác phải Safe-Skip máy. Sau 2 giờ không có người can thiệp, Reaper mới tự động thu hồi.

---

### Case LOCK-02: Destructive Actions Denylist (Cấm kill-server / pm clear làm sập farm)
- **Vị trí áp dụng:** Toàn bộ repository và script trên farm.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Gặp lỗi kết nối ADB đơn lẻ trên 1 máy, agent/script tự ý chạy `adb kill-server` hoặc `pm clear com.ss.android.ugc.trill`.
  - `adb kill-server` làm đứt toàn bộ socket của 160 máy đang chạy đồng thời, làm sập toàn bộ ca nuôi acc.
  - `pm clear` xóa sạch session đăng nhập, mất nick và bị TikTok phạt checkpoint.
- **Giải pháp chuẩn (Case Fix):**
  **NGHIÊM CẤM TUYỆT ĐỐI:** `adb kill-server`, `adb start-server`, `adb reboot`, `pm clear`. Mọi xử lý kết nối phải thao tác trên từng serial cụ thể (`adb -s <serial> ...`).

---

### Case LOCK-03: Proxy sập ➔ Fail-Closed (Cấm chạy Direct IP)
- **Vị trí áp dụng:** `automation_core/vpn.py`, `python_runner/flows/feed_swipe_smoke.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Khi VPN `tun0` bị ngắt hoặc proxy bị die, script tự động chạy tiếp bằng mạng gốc (Direct IP), dẫn tới hàng loạt nick cùng dính chung 1 địa chỉ IP mạng nội bộ và bị TikTok gắn cờ hàng loạt.
- **Giải pháp chuẩn (Case Fix):**
  **Fail-Closed tuyệt đối:** Nếu VPN/Proxy mất kết nối, thực hiện tối đa 1 lần recovery cấp lại proxy + reboot máy. Nếu vẫn không có IP proxy hợp lệ ➔ Dừng ngay với 0 swipes (`final_status: blocked-vichanger-vpn`), cấm tuyệt đối lướt bằng Direct IP.

---

### Case LOCK-04: Batch Reservation Lock Fault Isolation (Cô lập lỗi Lock/Guard từng máy, chống Crash toàn bộ Farm)
- **Vị trí áp dụng:** `python_runner/flows/multi_machine_feed_session.py`, `python_runner/run_tiktok.py`, `python_runner/core/device_lock.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern - Sự cố sáng 29/08/2026):**
  1. Trong vòng lặp đặt trước quyền truy cập thiết bị (`acquire_device_lock`) của `multi_machine_feed_session.py`, chỉ bắt `DeviceLockNeedsUserDecision` và `DeviceLockUnavailable`.
  2. Khi 1 máy gặp sự cố lock cấp transaction như `DeviceLockTransactionError` (ví dụ `DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE` do sót file `.takeover.lock` trên Máy 01 từ phiên trước) hoặc `DeviceLockReadinessError`, exception này kế thừa từ `RuntimeError` không được bắt trong vòng lặp `for account in accounts`.
  3. Hậu quả: Exception văng ra ngoài làm crash toàn bộ tiến trình batch runner, khiến 73 máy còn lại dù rảnh rỗi cũng bị dừng và không thể khởi chạy từ 06:00 đến 07:30.
- **Giải pháp chuẩn (Case Fix):**
  1. Mở rộng `except` trong vòng lặp reservation thành `(DeviceLockUnavailable, DeviceLockTransactionError, DeviceLockReadinessError)`.
  2. Ghi nhận log chi tiết lỗi cho máy đó, tạo fallback child artifact với `final_status="skipped-device-locked"` (`blocker_type: focus-device-issue`), và tiếp tục (`continue`) vòng lặp reserve cho tất cả các máy còn lại trong batch.
  3. Áp dụng tương tự cho hàm retry `reacquire_recovery_lock` và entrypoint single-machine `run_tiktok.py`.

---

### Case LOCK-05: Kế thừa Device Lock cho Subprocess Follow Hook (--skip-identity-verify)
- **Vị trí áp dụng:** `follow_runner/run_follow.py` trong repo `tiktok-follow`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Khi `multi_machine_feed_session.py` chạy lướt feed, nó giữ lock `project="tiktok-luot nuoi acc"`. Sau đó gọi `run_follow.py` làm hook follow. Trong `run_follow.py`, hàm preflight lock gọi `acquire_device_lock(user_authorized=False)`. Vì máy đang có lock từ tiến trình cha `tiktok-luot nuoi acc`, `run_follow.py` bắt `DeviceLockNeedsUserDecision` và tự exit code 2 (`BLOCKED: [device-lock]...`), khiến 100% lượt follow hook bị fail.
- **Giải pháp chuẩn (Case Fix):**
  Khi `run_follow.py` được gọi dưới cờ `--skip-identity-verify` (feed hook) và lock hiện tại thuộc về `tiktok-luot nuoi acc` / `tiktok-feed`, cho phép kế thừa quyền truy cập thiết bị mà không tự block chính mình.

---

## CHECKLIST KIỂM TRA BẮT BUỘC TRƯỚC KHI CHỐT PHIÊN
- [ ] Task có liên quan đến Farm Automation (UI, Cron, Sync, Lock, ADB, Workbook...)?
- [ ] Nếu có: Đã cập nhật chi tiết Case Fix thực tế và Anti-Pattern vào `docs/uiautomator.md` chưa?
- [ ] Đã chạy Unit Test hồi quy cho các module bị ảnh hưởng?
- [ ] Đã kiểm tra Gate 0 Live Canary (hoặc Gate 0.5 Document Gate) đầy đủ chưa?
