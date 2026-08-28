# UIAutomator & Popup Detection — Case Fix & Anti-Pattern Catalog

> **MANDATORY NOTICE CHO MỌI AGENT VÀ DEVELOPER:**
> File này lưu trữ toàn bộ các **Case Fix thực tế**, các **Cơ chế gây lỗi (Anti-Patterns)** và **Giải pháp chuẩn** cho các vấn đề tương tác UI, XML parsing, Popup Detection và Screen Navigation trên hệ thống farm thiết bị Taadaa.
> **BẮT BUỘC phải đọc và đối chiếu file này TRƯỚC KHI viết hoặc sửa bất kỳ script/handler UI nào.** Tuyệt đối không tái phạm các pattern gây lỗi đã được khắc phục ở các case dưới đây!

---

## Mục lục Case Fixes
1. [Case 1: False-Positive Camera Overlay trên trang Hồ sơ (Sự cố 28/08/2026)](#case-1-false-positive-camera-overlay-trên-trang-hồ-sơ-sự-cố-28082026)
2. [Case 2: Popup "Follow bạn bè của bạn" / Follow Suggestion](#case-2-popup-follow-bạn-bè-của-bạn--follow-suggestion)
3. [Case 3: Popup Xin quyền Vị trí (Location Permission Prompt)](#case-3-popup-xin-quyền-vị-trí-location-permission-prompt)
4. [Case 4: Overlay Trình duyệt In-App (Webview / Landing Page)](#case-4-overlay-trình-duyệt-in-app-webview--landing-page)
5. [Case 5: Màn hình Đổi Tên Hiển Thị (Edit Profile Name Subpage)](#case-5-màn-hình-đổi-tên-hiển-thị-edit-profile-name-subpage)
6. [Case 6: Popup "Hoạt động không có sẵn" (Activity Unavailable)](#case-6-popup-hoạt-động-không-có-sẵn-activity-unavailable)
7. [Case 7: Bàn phím ảo (IME) che khuất nút điều hướng dưới đáy](#case-7-bàn-phím-ảo-ime-che-khuất-nút-điều-hướng-dưới-đáy)
8. [Case 8: Gõ chuỗi ký tự đặc biệt / Mật khẩu bằng ADB thô](#case-8-gõ-chuỗi-ký-tự-đặc-biệt--mật-khẩu-bằng-adb-thô)

---

## Chi tiết từng Case Fix & Anti-Pattern

### Case 1: False-Positive Camera Overlay trên trang Hồ sơ (Sự cố 28/08/2026)
- **Vị trí áp dụng:** `flows/benign_popup_registry.py` (`_detect_camera_creation`), `flows/feed_swipe_smoke.py` (`_verify_profile_after_session`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Dùng cơ chế quét substring từ khóa chung chung:
  ```python
  # ❌ SAI LẦM: Quét substring thô trên toàn bộ XML dump
  markers = ["10 phút", "60s", "15s", "ẢNH", "VĂN BẢN", "10m", "Photo", "Templates", "CAMERA"]
  combined = ((xml_content or "") + " " + (ocr_text or "")).casefold()
  match_count = sum(1 for marker in markers if marker.casefold() in combined)
  return match_count >= 2
  ```
  Trên trang **Hồ sơ chuẩn** của TikTok luôn có `content-desc="Ảnh hồ sơ"` (khớp `ẢNH`) và `content-desc="Camera"` (khớp `CAMERA`). Kết quả `match_count >= 2` trả về `True` trên 100% máy bình thường. Script gửi phím BACK để "tắt camera" làm văng khỏi Profile về lại FYP, dẫn đến không tìm thấy username (`detected: null`) và báo lỗi giả `profile account mismatch`, kích hoạt khóa hiện trường (`status: blocked`) đồng loạt 28 máy.
- **Giải pháp chuẩn (Case Fix):**
  1. **BẮT BUỘC Negative Exclusions:** Nếu màn hình chứa các element của trang Hồ sơ (`Đã follow`, `Follower`, `Sửa hồ sơ`, `Số lượt xem hồ sơ`, `Menu hồ sơ`, `Thêm tiểu sử`...) hoặc thanh điều hướng đáy FYP (`Trang chủ` + `Hộp thư` / `Hồ sơ`), **LẬP TỨC TRẢ VỀ `False`**.
  2. **Yêu cầu cụm từ quay đặc thù:** Phải có ít nhất 2 chế độ quay (`15s`, `60s`, `10 phút`, `10m`, `templates`, `văn bản`, `tạo`) HOẶC 1 chế độ quay + 1 nút điều khiển camera (`lật`, `hẹn giờ`, `tốc độ`, `bộ lọc`, `thêm âm thanh`) HOẶC class `shortvideo` / `record_layout`.
  3. **Tách biệt lỗi UI và lỗi nick:** Không đọc được username do bấm trượt navigation (`detected: null`) tuyệt đối không được coi là lỗi tài khoản (`account mismatch`).

---

### Case 2: Popup "Follow bạn bè của bạn" / Follow Suggestion
- **Vị trí áp dụng:** `flows/benign_popup.py` (`detect_follow_friends_suggestion_popup`, `dismiss_follow_friends_suggestion_popup`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Tìm text `"Follow"` đơn thuần trên XML. Từ `"Follow"` xuất hiện ở nút Follow của video, caption bài đăng của creator, hoặc tab "Đang Follow", dẫn đến tap nhầm vào video hoặc bấm follow ngoài ý muốn làm đứt chuỗi lướt feed.
- **Giải pháp chuẩn (Case Fix):**
  1. Phải khớp chính xác chuỗi tiêu đề popup: `"Follow bạn bè của bạn"`, `"Đồng bộ danh bạ"`, `"Tìm bạn bè"`.
  2. Nút bấm dismiss ưu tiên: Nút `"Hủy"`, `"Để sau"`, `"Không phải bây giờ"`, icon `"close"`.
  3. Bỏ qua nếu từ khóa chỉ nằm trong thẻ caption video (`@resource-id="...desc"` hoặc `...title`).

---

### Case 3: Popup Xin quyền Vị trí (Location Permission Prompt)
- **Vị trí áp dụng:** `flows/benign_popup_registry.py` (`_detect_location_prompt`, `_dismiss_location_prompt`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Bấm phím BACK để thoát popup vị trí. Trên một số phiên bản TikTok / Android, bấm BACK khi dialog hệ thống đang mở sẽ đóng luôn cả Activity chính của TikTok, làm app rơi vào background và fail preflight.
- **Giải pháp chuẩn (Case Fix):**
  1. Tìm Node nút `"Hủy"`, `"Không cho phép"`, `"Từ chối"`, `"Trong khi dùng ứng dụng"`, `"Chỉ lần này"` qua XML.
  2. Tap trực tiếp vào tọa độ/bounds của nút `"Hủy"` / `"Từ chối"`.
  3. Fallback gửi phím BACK chỉ khi không tìm thấy bounds của nút, và sau đó phải kiểm tra lại `get_focused_activity` để đảm bảo TikTok vẫn ở foreground.

---

### Case 4: Overlay Trình duyệt In-App (Webview / Landing Page)
- **Vị trí áp dụng:** `flows/benign_popup_registry.py` (`_detect_inapp_browser`, `_dismiss_inapp_browser`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Khi lướt gặp video quảng cáo có nút CTA "Tìm hiểu thêm", "Tải ngay", "Xem chi tiết", nếu tap nhầm sẽ mở Webview toàn màn hình. Script cũ liên tục bấm BACK nhiều lần làm back xuyên qua lịch sử duyệt web rồi thoát thẳng ra màn hình Launcher Android.
- **Giải pháp chuẩn (Case Fix):**
  1. Nhận diện Webview qua `class="android.webkit.WebView"` hoặc resource-id chứa `cross_btn`, `close_btn`, `btn_close`, `iv_close`.
  2. Bấm nút Đóng (`X`) ở góc trên màn hình để đóng triệt để Webview thay vì bấm BACK lặp vòng.

---

### Case 5: Màn hình Đổi Tên Hiển Thị (Edit Profile Name Subpage)
- **Vị trí áp dụng:** `flows/benign_popup_registry.py` (`_detect_edit_name`, `_dismiss_edit_name`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Tài khoản mới reg hoặc chưa đặt tên mở trang Hồ sơ sẽ bị chặn bởi màn hình "Thêm tên bạn mong muốn" (yêu cầu đặt tên hoặc đổi tên). Script không nhận diện được sẽ tưởng bị kẹt profile hoặc crash.
- **Giải pháp chuẩn (Case Fix):**
  1. Nhận diện qua chuỗi `"Thêm tên bạn mong muốn"` hoặc `"Đổi tên một lần mỗi 7 ngày"`.
  2. Tự động sinh tên tiếng Việt tự nhiên qua `make_tiktok_name(email)`.
  3. Nhập tên an toàn qua `AdbKeyboard` Base64 (tránh lỗi ký tự tiếng Việt có dấu).
  4. Ẩn bàn phím, tap nút Lưu `[990, 138]` và nút xác nhận Đặt tên `[750, 1175]`.

---

### Case 6: Popup "Hoạt động không có sẵn" (Activity Unavailable)
- **Vị trí áp dụng:** `flows/benign_popup_registry.py` (`_detect_activity_unavailable`, `_dismiss_activity_unavailable`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  TikTok hiện dialog "Hoạt động không có sẵn. Vui lòng chuyển sang tài khoản ban đầu đã dùng trên thiết bị này". Nếu không đóng, màn hình bị mờ đục và khóa mọi thao tác vuốt.
- **Giải pháp chuẩn (Case Fix):**
  1. Nhận diện qua title `"Hoạt động không có sẵn"` / `"Activity not available"` VÀ nội dung `"chuyển sang tài khoản ban đầu"` / `"switch to the original account"`.
  2. Gửi lệnh BACK hoặc tap vùng ngoài dialog để dismiss an toàn, sau đó khôi phục lại luồng vuốt feed.

---

### Case 7: Bàn phím ảo (IME) che khuất nút điều hướng dưới đáy
- **Vị trí áp dụng:** `flows/feed_swipe_smoke.py`, `core/keyboard.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Sau khi tìm kiếm, nhập comment hoặc đổi tên, bàn phím Samsung Keypad / Gboard vẫn nổi trên màn hình che khuất thanh điều hướng đáy (`[0, 1794][1080, 1920]`). Lệnh tap vào Profile `[972, 1857]` chạm trúng phím Enter/Dấu cách của bàn phím ảo thay vì icon Hồ sơ.
- **Giải pháp chuẩn (Case Fix):**
  1. Trước khi thực hiện tap điều hướng (Home, Inbox, Profile), gọi bước `cleanup_keyboard_before_nav` (gửi `input keyevent 111` - KEYCODE_ESCAPE hoặc chuyển IME về trạng thái ẩn).
  2. Kiểm tra `mInputShown` qua `dumpsys input_method` để đảm bảo bàn phím đã hạ hoàn toàn.

---

### Case 8: Gõ chuỗi ký tự đặc biệt / Mật khẩu bằng ADB thô
- **Vị trí áp dụng:** Toàn bộ runner và flow login/register/2FA.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Dùng `adb shell input text "P@ssw0rd!"` thô. Shell Linux/Android sẽ nuốt/escape các ký tự `@`, `!`, `&`, `#`, `$`, `%`, khoảng trắng, dẫn đến mật khẩu điền bị thiếu ký tự và báo lỗi sai mật khẩu giả tạo (sự cố m76).
- **Giải pháp chuẩn (Case Fix):**
  1. **BẮT BUỘC** dùng `AdbKeyboard` qua broadcast base64:
     `adb shell am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <base64_encoded_string>`
  2. Đổi IME sang `com.github.uiautomator/.AdbKeyboard` trước khi điền và đổi lại `SamsungKeypad` sau khi hoàn tất.

---

## 3. Checklist tự kiểm tra trước khi commit/push thay đổi UI
- [ ] Hàm detect có đầy đủ **Negative Exclusions** (loại trừ Profile, FYP, Bottom Nav)?
- [ ] Không sử dụng substring thô từ khóa ngắn (`ảnh`, `camera`, `video`, `text`) trên toàn bộ XML?
- [ ] Lệnh dismiss có điểm đến an toàn, không làm crash/thoát app?
- [ ] Đã chạy test đối soát qua toàn bộ các dump XML thực tế trong thư mục `/runtime/kibe/live/...`?
- [ ] Tất cả unit tests liên quan trong `python_runner/tests/` đã chạy và PASS 100%?
