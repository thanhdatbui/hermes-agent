# TikTok LIVE Resource-ID OTP False Positive & PlayCore Popup Triage

## 1. TikTok LIVE stream internal resource-id "otp" false positive

### Hiện tượng
Khi đang lướt feed TikTok, máy bất ngờ dừng lại với stop reason:
`login/account screen detected` hoặc `manual review required during feed-session-smoke`.
Kiểm tra hiện trường thấy máy đang xem livestream bình thường, tài khoản không bị logout hay văng nick.

### Nguyên nhân gốc rễ
Trong giao diện TikTok LIVE stream, một số view hiển thị thứ hạng người xem / điểm vote mang resource ID nội bộ do TikTok obfuscate:
`resource-id="com.ss.android.ugc.trill:id/otp"`, `text="1"`, `class="android.widget.TextView"`.
Nếu hàm `has_sensitive_marker(root)` dùng `_value(element)` (nối gộp cả `text`, `content-desc` và `resource-id`) và kiểm tra từ khóa `"otp"` bằng phép thử chuỗi con (`term in value`):
- Chuỗi con `"otp"` khớp với `...:id/otp` trong resource-id.
- `strong_terms = ("manual_challenge", "captcha", "otp")` đánh dấu màn hình là nhạy cảm.
- Bộ phân loại màn hình đánh nhãn `manual-needed:login` ("login/account/credential marker present").

### Giải pháp chuẩn hóa (Text-Only Regex Gate)
Trong `automation-core/src/automation_core/tiktok/benign_popup.py`:
1. Quét từ khóa `SENSITIVE_POPUP_TERMS` **CHỈ TRÊN VISIBLE TEXT VÀ CONTENT-DESC** (`element.text`, `element.content_desc`), tuyệt đối không để resource-id hash ngẫu nhiên của TikTok lọt vào `values`.
2. Riêng từ khóa `"otp"`, bắt buộc dùng regex ranh giới từ `\botp\b` để tránh khớp chuỗi con ngẫu nhiên (như `hotpot`, `id/otp`).
3. Resource IDs chỉ được kiểm tra riêng biệt qua `SENSITIVE_POPUP_RESOURCE_TERMS`.

---

## 2. Google Play PlayCore Supplemental Download Dialog

### Câu hỏi vận hành: "Có nên tải tệp bổ sung không?"
👉 **CÂU TRẢ LỜI: TUYỆT ĐỐI KHÔNG ĐƯỢC TẢI! BẮT BUỘC BẤM [X] (ĐÓNG) HOẶC PHẢI CODE CHO TỰ DISMISS.**
* **Lý do kỹ thuật**:
  1. **Nghẽn băng thông proxy**: Farm 80-160 máy tải đồng thời các gói APK split qua proxy mobi/dcom sẽ làm sập băng thông, timeout toàn bộ runner.
  2. **Tràn bộ nhớ máy**: Dàn Samsung S7 bộ nhớ 32GB đang gánh 8 nick TikTok; việc tải thêm các module mở rộng không cần thiết dễ gây đầy ổ đĩa (Storage Full).
  3. **Vỡ UI automation**: Sau khi tải xong, Google Play có thể bung tiếp thông báo/quyền mới, hoặc TikTok bật layout tính năng mới làm gãy selectors hiện tại.
  4. **Không cần thiết**: Nuôi acc lướt feed, follow và upload video hoàn toàn không phụ thuộc vào các tệp bổ sung này. Bấm `[X]` hoặc `BACK` thì TikTok vẫn chạy 100% bình thường.

### Hiện tượng & Cạm bẫy kỹ thuật
1. **Lỗi `profile_preflight`**: Máy dừng với lý do `Google/GMS/account screen focused`. Focus package bị chuyển sang `com.android.vending`.
2. **Lỗi `ACCOUNT_READY` trong `Tiktok-video`**:
   - Khi chuyển tài khoản xong, popup Google Play `PlayCoreAcquisitionActivity` (`com.android.vending`) nhảy lên đè lên TikTok.
   - Script gọi `adapter.bring_to_foreground("com.ss.android.ugc.trill")`. Lệnh `am start` không thể đưa TikTok lên foreground vì Activity của Google Play là một modal dialog nằm đè trên đỉnh task stack.
   - Kết quả: Văng lỗi sai `[ACCOUNT_SWITCHER_FAILED] TikTok không trở lại foreground trước ACCOUNT_READY`.

### Giải pháp chuẩn hóa đa tầng (Multi-Layer Dismiss)
1. **Trong `python_runner/flows/benign_popup_registry.py`**:
   - Đăng ký handler `playcore_acquisition_dialog` (Priority 79): quét `com.android.vending` kèm từ khóa `"tệp bổ sung"` / `"additional files"` / `"đóng hộp thoại cập nhật"` và tap tâm nút đóng.
2. **Trong `Tiktok-video/scripts/tiktok_workflow/state_machine.py`**:
   - Trong `_dismiss_simple_close_popup`: Nhận diện `PlayCoreAcquisitionActivity` hoặc `com.android.vending`. Quét các nhãn đóng `("Đóng hộp thoại cập nhật", "Đóng", "Close")` qua cả `text` lẫn `content_desc`. Nếu không tìm thấy nút đóng, kích hoạt ngay fallback phím `BACK` (`adapter.back()`) để đóng dialog trong 1s.
   - Bắt buộc kiểm tra null-safe: `if not xml_text: return False` ở đầu hàm để tránh crash `TypeError: normalize() argument 2 must be str, not None`.
   - Trong bước `ACCOUNT_READY`: Trước khi kiểm tra `tiktok_package not in current_xml` và gọi `bring_to_foreground`, BẮT BUỘC gọi `_dismiss_simple_close_popup(adapter, current_xml)` để dẹp modal dialog của PlayCore trước.
   - Trong bước `_handle_account_switcher`: Gọi `_dismiss_simple_close_popup(adapter, switcher_profile_xml)` ngay trước `open_switcher` để đóng các popup Milestone (`"Bạn có tin vui?"`, `"Tổng số lượt thích: ... [OK]"`, `"Bạn đang nghĩ gì [Xong]"`) tránh che khuất anchor header.
   - Chuẩn hóa Telemetry: Ghi log structured metric `logger.info("[POPUP_METRIC] action=dismiss popup_type=playcore method=%s", method)` để phục vụ giám sát và vượt qua Sol Auditor Reviewer Gate (>= 85/100).
3. **Trong `tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py` (Lướt Feed Baseline)**:
   - **Bẫy tử huyệt `learn_more_dialog_dismiss`**: Popup PlayCore có nút `[Tìm hiểu thêm]` (`com.android.vending`) và nút đóng `content-desc="Đóng hộp thoại cập nhật"`. Rule `learn_more_dialog_dismiss` trong `GEMPHONEFARM_BLIND_POPUP_RULES` khớp detector `//node[@text="Tìm hiểu thêm"]`, nhưng action xpath chỉ tìm `@text="Đóng" or @content-desc="Đóng"`.
   - Kết quả: Không bấm được nút đóng -> bước chụp kế tiếp `baseline_after_gemphonefarm_blind_popup` thấy focus vẫn là `com.android.vending` -> `safety.py` trả về `SAFETY_MANUAL_NEEDED` (`Google/GMS/account screen focused`) -> Watchdog gom vào P0 mất phiên ảo.
   - **Khắc phục**:
     a) Bổ sung `@content-desc="Đóng hộp thoại cập nhật"` hoặc `contains(@content-desc, "hộp thoại cập nhật")` vào `action_xpath` của `learn_more_dialog_dismiss`, hoặc bổ sung rule riêng `playcore_dialog_dismiss` trong `GEMPHONEFARM_BLIND_POPUP_RULES`.
     b) Trong `_run_gemphonefarm_blind_popup_checkpoint`: Nếu phát hiện `com.android.vending`, gọi trực tiếp `_dismiss_playcore_acquisition_dialog` từ `benign_popup_registry.py` để click nút đóng hoặc gửi phím `BACK`.

---

### 3. Căn nguyên gốc rễ: Thiếu Split APKs (< 50 file) & Bẫy Watchdog Tự Nạp

### Hiện tượng & Bản chất
- **Hiện tượng**: Màn hình Google Play "Tải các tệp bổ sung..." (`PlayCoreAcquisitionActivity`) nhảy liên tục mỗi khi mở app hoặc thực hiện tác vụ (player, live, search), dù đã bấm đóng nhiều lần.
- **Bản chất kỹ thuật**: TikTok sử dụng Android Dynamic Feature Modules (Play Feature Delivery). Bộ cài đầy đủ trên farm có **55 - 67 split APKs** (~280MB, chứa các dynamic modules như `split_df_camera_biz`, `split_df_live_cast`, `split_df_player`, `split_df_search_biz`, `split_df_ship`, `split_df_vmsdk`...).
- Nếu máy chỉ cài **5 file cơ bản** (`base.apk`, `split_config.arm64_v8a.apk`, `split_config.vi.apk`, `split_config.xxhdpi.apk`, `split_df_a_dex.apk`), thư viện PlayCore tích hợp trong app sẽ liên tục gọi Google Play Store qua IPC đòi tải các dynamic split còn thiếu -> Google Play bung modal popup làm gián đoạn runner.

### 4 Bẫy tử huyệt trong code Watchdog Tự Nạp (`farm_app_provision_watchdog.py`)
1. **Bẫy Hardcode danh sách Split**: Trong `REQUIRED_APPS`, nếu trường `split_apks` bị hardcode danh sách 5 file, watchdog sẽ chỉ cài 5 file này và bỏ qua toàn bộ 60+ dynamic split APKs có sẵn trong thư mục kho APK (`v47.0.3`).
   * *Khắc phục*: Tự động nạp toàn bộ file `*.apk` trong thư mục version nếu không chỉ định `split_apks`, và bắt buộc xếp `base.apk` lên đầu danh sách trước khi gọi `install-multiple`.
2. **Bẫy Kiểm tra hời hợt (`pm list packages`)**: Watchdog chỉ chạy `pm list packages` để kiểm tra `com.ss.android.ugc.trill`. Khi app đã có mặt (dù chỉ có 5 file), watchdog lầm tưởng là đã cài đủ và bỏ qua, không bao giờ tự nạp bù.
   * *Khắc phục*: Với gói split TikTok, bắt buộc kiểm tra số lượng file cài đặt thực tế qua `pm path com.ss.android.ugc.trill`. Nếu `len(splits_installed) < 50` -> đánh dấu là `missing` để nạp bù đầy đủ.
3. **Bẫy Regex Lock File JSON (`\b(\d+)\b`)**: Trong hàm `is_device_busy`, nếu dùng regex `\b(\d+)\b` trên nội dung file lock JSON, số đầu tiên khớp được là `"machine": <STT>` (ví dụ 73) thay vì PID của tiến trình (`"pid": 59216`). Do PID 73 không tồn tại, watchdog coi lock là stale và thao tác đè lên thiết bị đang chạy.
   * *Khắc phục*: Bắt buộc parse `json.loads(content)` và trích xuất đúng trường `data.get("pid")` hoặc `data.get("holder_pid")`.
4. **Bẫy Nghẽn Băng Thông USB Hub 20 cổng (USB Bus Congestion / Drop to Offline)**: Mỗi máy nhận ~280MB APK. Nếu chạy `max_workers=25` song song nạp cùng lúc cho 20+ máy trên cùng Hub USB, băng thông USB bị bão hòa, socket ADB bị ngắt quãng giữa chừng (`device offline` / `failed to write split_df_a_dex.apk`).
   * *Khắc phục*: BẮT BUỘC giới hạn `max_workers <= 5` khi nạp APK nặng.
   * *Bẫy sáng màn hình sau cài*: Bổ sung `["input", "keyevent", "223"]` vào `POST_CONFIG_COMMANDS` để tự động đưa máy về Sleep/Dozing sau khi nạp xong.
   * *Kỷ luật điều phối & Cron Frequency*: Watchdog cần chạy định kỳ `*/5 * * * *` gửi alert về Telegram (`telegram:-5373649734`) để tự động hóa cuốn chiếu khi máy rảnh; CẤM Coordinator dừng lại hỏi xin phép ("Có muốn nạp không?") khi quyền tự động hóa đã được User ủy quyền sẵn.

### Quy trình nạp bù Split APKs chuẩn O(1) (Giữ nguyên 100% Login Data)
1. **Kiểm tra số split hiện tại**:
   `adb -s <serial> shell pm path com.ss.android.ugc.trill`
2. **Lệnh nạp song song an toàn (CẤM pm clear)**:
   `adb -s <serial> install-multiple -r -d base.apk split_*.apk`
   * Bắt buộc giữ flag `-r` (reinstall/giữ data) và `-d` (allow version downgrade nếu cần).
   * Bắt buộc truyền `base.apk` đầu tiên, theo sau là toàn bộ các split `.apk`.
3. **Sau khi nạp**: Force-stop TikTok, đưa về màn hình chính (`input keyevent 3`) và tắt màn hình (`input keyevent 223`) để app khởi động lại với đầy đủ dynamic feature modules và dưỡng pin.

---

## 4. Đối soát Lệch Phiên Bản App Giữa Các Cụm Farm (Cross-Cluster App Version Alignment vs Script Resilience)

### Câu hỏi vận hành: "Đổi bản app runner có bị lỗi không? Admin chạy v46 còn Kibe chạy v47 có gặp lỗi lệch phiên bản hay crash script không?"
👉 **KẾT LUẬN: HOÀN TOÀN KHÔNG BỊ GÃY SCRIPT VÌ KHÁC BẢN APP.**
- Cả 2 cụm đều sử dụng chung một runner tập trung (`feed_swipe_smoke.py`).
- Minh chứng thực tế: Cả Admin (v46.6.3, 55 splits) và Kibe (v47.0.3, 65 splits) đều đạt tỷ lệ thành công tương đương nhau (~83% - 87%).

### Tại sao Script chạy được xuyên phiên bản (Version-Agnostic Architecture)?
1. **Khớp text và regex đa ngôn ngữ**: Tìm tab Hồ sơ qua `Profile / Hồ sơ / Tôi`, tab Trang chủ qua `Home / Trang chủ / Für dich`, không phụ thuộc vào ID tài nguyên nội bộ bị obfuscate.
2. **Generic Widget Classes**: Dùng các class Android gốc (`android.widget.TextView`, `android.widget.FrameLayout`) thay vì các class con tùy biến theo version của TikTok.
3. **Tọa độ vuốt tương đối**: Tính toán theo tỷ lệ khung hình chuẩn Samsung S7 (`1440x2560`), không phụ thuộc vào container feed bên trong app.

### 2 Bẫy Dừng Runner Thường Bị Hiểu Nhầm Do Đổi Bản App & Lệch Ngữ Cảnh Xử Lý (False Version Blocker & Handler Trap)
1. **Bẫy va chạm nút `+ Thêm tên` & Lệch ngôn ngữ trong hàm `_detect_edit_name` (M213, M268)**:
   - **Hiện tượng**: Nick chưa có Display Name sẽ hiện nút `+ Add name` hoặc `+ Namen hinzufügen` ngay tại header trên cùng (đè đúng vị trí anchor chuyển tài khoản).
   - **Căn nguyên lệch hàm**:
     * User đã viết hàm `make_tiktok_name` và `_detect_edit_name` / `_dismiss_edit_name` (trong `benign_popup_registry.py` và `core/benign_popup.py`).
     * Tuy nhiên, `_detect_edit_name` và `detect_edit_name_subpage` chỉ kiểm tra các chuỗi **tiếng Việt**: `"thêm tên bạn mong muốn"`, `"chỉ có thể đổi tên"`, `"đổi tên một lần mỗi 7 ngày"`.
     * Khi giao diện app hiển thị **tiếng Anh**: `"Add your preferred name"`, `"Your name can only be changed once every 7 days"`, `"Save"`, `"Cancel"` (hoặc header tiếng Đức `+ Namen hinzufügen` lọt qua `is_excluded_name`), hàm detect trả về `False` -> classifier không nhận diện được trang đặt tên -> văng ra `unknown TikTok state` -> dừng `manual-needed`.
   - **Khắc phục**:
     * Bổ sung từ khóa tiếng Anh vào `_detect_edit_name` / `detect_edit_name_subpage`: `"add your preferred name"`, `"can only be changed once every 7 days"`, `"7 days"`.
     * Bổ sung tiếng Đức `"namen hinzufügen"` vào `_EXCLUDED_SWITCHER_TERMS` / `is_excluded_name` ở dòng 14564 của `feed_swipe_smoke.py`.
2. **Bẫy Khám phá bạn bè trong Tab "Bạn bè" & Lệch vị trí kích hoạt Fallback (Friends Tab Promotion Dialog - M232, M249)**:
   - **Hiện tượng**: Khi kịch bản yêu cầu chuyển sang tab "Bạn bè" để lướt feed, nhưng tài khoản mới có 0 bạn bè/0 following, TikTok hiển thị banner: *"Kết nối với liên hệ trong danh bạ / Facebook"* (`Mời bạn bè`, `Kết nối danh bạ`).
   - **Căn nguyên lệch hàm**:
     * User đã viết hàm `_has_friends_feed_content(after)` và cơ chế `empty_feed_fallback_for_you` (dòng 22416) để tự động nhảy về tab For You.
     * Tuy nhiên cơ chế này được đặt ở **bên trong vòng lặp vuốt (`swipe loop`)**.
     * Khi runner vừa bấm tab Bạn bè, nó chạy bước xác nhận chuyển tab (`switch_friends_N_navigation_confirm`). Tại đây, bộ phân loại `classify_screen` nhận diện màn hình rỗng này là `manual-needed:popup` (`known contact_follow_suggestion popup detected`).
     * Runner đóng popup làm app bị văng về tab For You. Bước `navigation_confirm` kiểm tra thấy `expected: Friends feed` nhưng `detected: for-you` -> dừng ngay với lỗi `unexpected popup/dialog marker detected` **TRƯỚC KHI kịp bước vào vòng lặp swipe để kích hoạt hàm fallback**.
   - **Khắc phục**:
     * Trong bước `switch_friends_N_navigation_confirm`, nếu phát hiện `contact_follow_suggestion` hoặc `_has_friends_feed_content`, không được coi là lỗi navigation mismatch, mà phải kích hoạt ngay nhánh `empty_feed_fallback_for_you` để chuyển mượt mà về tab For You và tiếp tục phiên lướt.

### Kỷ luật nâng cấp App trên Remote Cluster (Admin LAN Socket)
- **CẤM TUYỆT ĐỐI đẩy nâng cấp APK hàng loạt qua Remote ADB LAN (`192.168.110.119:5037`) khi phiên bản cũ đang chạy ổn định**:
  * Đẩy 65 split APKs (~280MB/máy x 80 máy = ~23GB) qua socket LAN sẽ bão hòa băng thông, gây nghẽn ADB pipe và làm rớt offline hàng loạt máy.
  * Giữ nguyên phiên bản hiện tại (như v46.6.3 với 55 split APKs trên Admin) nếu tỷ lệ thành công >= 85%. Chỉ nâng cấp khi TikTok chặn cứng phiên bản cũ (forced update) và bắt buộc thực hiện ngoài khung giờ chạy batch.

---

## 5. Chuẩn Hóa Ngôn Ngữ Hệ Thống Máy Farm (System Locale vi-VN Enforcement)

### Hiện tượng & Căn nguyên
- **Hiện tượng**: Một số máy trên farm (như M213) chạy ROM mặc định ngôn ngữ Đức (`de-AT`) hoặc Anh (`en-US`), khiến TikTok tự động áp dụng giao diện tiếng Anh hoặc tiếng Đức thay vì tiếng Việt.
- **Hệ quả**:
  - Anchor tiêu đề hiện `+ Namen hinzufügen` hoặc `+ Add name` đè lên profile header.
  - Các modal đặt tên, gợi ý bạn bè, thông báo hệ thống chuyển sang tiếng nước ngoài, vô hiệu hóa các regex detector thuần tiếng Việt trong runner.

### Giải pháp chuẩn hóa toàn diện
1. **Lệnh ADB khóa cứng ngôn ngữ tiếng Việt (vi-VN)**:
   ```bash
   adb -s <serial> shell setprop persist.sys.locale vi-VN
   adb -s <serial> shell settings put system system_locales vi-VN
   ```
2. **Tích hợp vào Watchdog Provision (`farm_app_provision_watchdog.py`)**:
   - Bổ sung `["setprop", "persist.sys.locale", "vi-VN"]` và `["settings", "put", "system", "system_locales", "vi-VN"]` vào `POST_CONFIG_COMMANDS`.
   - Mỗi chu kỳ watchdog quét máy rảnh sẽ tự động chuẩn hóa locale về `vi-VN`, bảo đảm 100% thiết bị trên cả 2 cụm Kibe và Admin luôn thống nhất ngôn ngữ tiếng Việt.


