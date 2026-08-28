# Taadaa Farm Automation — Case Fix & Anti-Pattern Catalog

> **MANDATORY NOTICE CHO MỌI AGENT VÀ DEVELOPER TOÀN HỆ THỐNG:**
> File này là **Knowledge Base sống** lưu trữ toàn bộ các **Case Fix thực tế**, các **Cơ chế gây lỗi (Anti-Patterns)** và **Giải pháp chuẩn** trong toàn bộ hệ sinh thái Farm Automation (bao gồm: UI/UIAutomator, Cron/Scheduler/Watchdog, Sync/Workbook/Data Integrity, Device Lock & ADB Lifecycle).
> 
> **QUY TẮC CHỐT PHIÊN BẮT BUỘC:**
> Bất kỳ phiên làm việc nào có sửa đổi logic code/config liên quan đến Farm Automation, trước khi Model Review và Commit **BẮT BUỘC phải cập nhật Case Fix thực tế và Anti-Pattern tương ứng vào file này**.
> Khi bắt đầu nhận task hoặc sửa script, **BẮT BUỘC phải đọc và đối chiếu file này** để tuyệt đối không tái phạm các pattern gây lỗi đã được khắc phục dưới đây.

---

## Mục lục Phân loại

- [PHẦN 1: UI, UIAUTOMATOR & POPUP DETECTION](#phần-1-ui-uiautomator--popup-detection)
  - [Case UI-01: False-Positive Camera Overlay trên trang Hồ sơ (Sự cố 28/08/2026)](#case-ui-01-false-positive-camera-overlay-trên-trang-hồ-sơ-sự-cố-28082026)
  - [Case UI-02: Popup "Follow bạn bè của bạn" / Follow Suggestion](#case-ui-02-popup-follow-bạn-bè-của-bạn--follow-suggestion)
  - [Case UI-03: Popup Xin quyền Vị trí (Location Permission Prompt)](#case-ui-03-popup-xin-quyền-vị-trí-location-permission-prompt)
  - [Case UI-04: Overlay Trình duyệt In-App (Webview / Landing Page)](#case-ui-04-overlay-trình-duyệt-in-app-webview--landing-page)
  - [Case UI-05: Màn hình Đổi Tên Hiển Thị Profile (Edit Name Subpage)](#case-ui-05-màn-hình-đổi-tên-hiển-thị-profile-edit-name-subpage)
  - [Case UI-06: Popup "Hoạt động không có sẵn" (Activity Unavailable)](#case-ui-06-popup-hoạt-động-không-có-sẵn-activity-unavailable)
  - [Case UI-07: Bàn phím ảo (IME) che khuất thanh điều hướng đáy](#case-ui-07-bàn-phím-ảo-ime-che-khuất-thanh-điều-hướng-đáy)
  - [Case UI-08: Gõ mật khẩu / chuỗi ký tự đặc biệt bằng ADB thô](#case-ui-08-gõ-mật-khẩu--chuỗi-ký-tự-đặc-biệt-bằng-adb-thô)
- [PHẦN 2: CRON, SCHEDULER & WATCHDOG](#phần-2-cron-scheduler--watchdog)
  - [Case CRON-01: Lệch pha giữa Cron Dọn dẹp (Reaper) và Cron Thông báo (Watchdog)](#case-cron-01-lệch-pha-giữa-cron-dọn-dẹp-reaper-và-cron-thông-báo-watchdog)
  - [Case CRON-02: Runner Live Lease & Shift Isolation (Chống treo PID cũ cản trở ca sau)](#case-cron-02-runner-live-lease--shift-isolation-chống-treo-pid-cũ-cản-trở-ca-sau)
  - [Case CRON-03: Chống Double Spawn khi Runner hoàn tất giữa chừng](#case-cron-03-chống-double-spawn-khi-runner-hoàn-tất-giữa-chừng)
- [PHẦN 3: SYNC, WORKBOOK & DATA INTEGRITY](#phần-3-sync-workbook--data-integrity)
  - [Case SYNC-01: Race Condition khi ghi file taikhoan_run_safe trên OneDrive 2 PC](#case-sync-01-race-condition-khi-ghi-file-taikhoan_run_safe-trên-onedrive-2-pc)
  - [Case SYNC-02: Parse Device ID / Serial bị dính định dạng Ngày tháng trong Excel](#case-sync-02-parse-device-id--serial-bị-dính-định-dạng-ngày-tháng-trong-excel)
  - [Case SYNC-03: Daily Cooldowns File Lock (.flock) và cơ chế Check-and-Reserve UUID](#case-sync-03-daily-cooldowns-file-lock-flock-và-cơ-chế-check-and-reserve-uuid)
- [PHẦN 4: DEVICE LOCK & ADB LIFECYCLE](#phần-4-device-lock--adb-lifecycle)
  - [Case LOCK-01: Giữ nguyên hiện trường Lock Blocked đủ TTL 2h (Cấm tự tiện Unlock vội)](#case-lock-01-giữ-nguyên-hiện-trường-lock-blocked-đủ-ttl-2h-cấm-tự-tiện-unlock-vội)
  - [Case LOCK-02: Destructive Actions Denylist (Cấm kill-server / pm clear làm sập farm)](#case-lock-02-destructive-actions-denylist-cấm-kill-server--pm-clear-làm-sập-farm)
  - [Case LOCK-03: Proxy sập -> Fail-Closed (Cấm chạy Direct IP)](#case-lock-03-proxy-sập---fail-closed-cấm-chạy-direct-ip)

---

## PHẦN 1: UI, UIAUTOMATOR & POPUP DETECTION

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
  Trang Hồ sơ chuẩn luôn có `content-desc="Ảnh hồ sơ"` và nút `content-desc="Camera"` -> `match_count >= 2` luôn đúng. Script gửi phím BACK để "tắt camera" làm văng khỏi Profile về lại FYP, không đọc được username (`detected: null`), báo lỗi giả `profile account mismatch` và kích hoạt `status: blocked` trên 28 máy.
- **Giải pháp chuẩn (Case Fix):**
  1. **Negative Exclusions:** Kiểm tra loại trừ nếu màn hình có các trường của Profile (`Đã follow`, `Follower`, `Sửa hồ sơ`, `Menu hồ sơ`...) hoặc thanh điều hướng đáy FYP (`Trang chủ` + `Hộp thư` / `Hồ sơ`) -> Trả về `False` ngay lập tức.
  2. **Yêu cầu cụm từ chế độ quay đặc thù:** Tối thiểu 2 chế độ quay (`15s`, `60s`, `10 phút`, `10m`, `templates`, `văn bản`, `tạo`) HOẶC 1 chế độ quay + 1 công cụ camera (`lật`, `hẹn giờ`, `tốc độ`, `bộ lọc`, `thêm âm thanh`).
  3. **Độc lập lỗi:** Không đọc được username do bấm trượt navigation (`detected: null`) KHÔNG ĐƯỢC coi là lỗi tài khoản (`account mismatch`).

---

### Case UI-02: Popup "Follow bạn bè của bạn" / Follow Suggestion
- **Vị trí áp dụng:** `python_runner/flows/benign_popup.py` (`detect_follow_friends_suggestion_popup`, `dismiss_follow_friends_suggestion_popup`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Tìm text `"Follow"` chung chung -> Khớp vào nút Follow của video đang phát hoặc caption creator, gây tap nhầm follow ngoài ý muốn làm đứt chuỗi lướt feed.
- **Giải pháp chuẩn (Case Fix):**
  1. Khớp chính xác cụm tiêu đề: `"Follow bạn bè của bạn"`, `"Đồng bộ danh bạ"`, `"Tìm bạn bè"`.
  2. Nút bấm dismiss ưu tiên: `"Hủy"`, `"Để sau"`, `"Không phải bây giờ"`, icon `"close"`.
  3. Bỏ qua nếu từ khóa nằm trong node caption video (`@resource-id="...desc"` hoặc `...title`).

---

### Case UI-03: Popup Xin quyền Vị trí (Location Permission Prompt)
- **Vị trí áp dụng:** `python_runner/flows/benign_popup_registry.py` (`_detect_location_prompt`, `_dismiss_location_prompt`).
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Bấm phím BACK để tắt dialog vị trí -> Trên một số bản Android/TikTok, bấm BACK khi permission dialog mở sẽ đóng luôn Activity chính của TikTok, làm app rơi vào background.
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

## PHẦN 2: CRON, SCHEDULER & WATCHDOG

### Case CRON-01: Lệch pha giữa Cron Dọn dẹp (Reaper) và Cron Thông báo (Watchdog)
- **Vị trí áp dụng:** `deploy/hermes-home/scripts/watch_device_locks.py`, `scripts/reap-dead-owner-locks.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Reaper chạy định kỳ `XX:00, XX:15, XX:30, XX:45`. Watchdog chạy ở `XX:11, XX:26, XX:41, XX:56`. Lock vừa chạm 120 phút ở `XX:52` thì Watchdog quét thấy lúc `XX:56` và bắn cảnh báo Telegram `⚠️ QUÁ HẠN > 2H`, trong khi Reaper đến `XX:00` mới đến lịch dọn -> Tạo ra cảnh báo rác "Tại sao quá 2h đéo tự unlock".
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
  Quét publications terminal (`collect_publications`) của cohort hiện tại. Lọc bỏ các máy đã có kết quả terminal, chỉ spawn những máy còn thiếu. Nếu tất cả máy đã terminal -> Thu hồi lease và không spawn lại.

---

## PHẦN 3: SYNC, WORKBOOK & DATA INTEGRITY

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
  Kiểm tra Regex định dạng Serial chuẩn (chuỗi hex/alphanumeric hợp lệ, độ dài chuẩn, không chứa ký tự `/`, `-`, `:` của ngày tháng). Nếu dính text ngày -> Tự động tra cứu fallback sang `config-machine-XX.yaml` hoặc mapping canonical.

---

### Case SYNC-03: Daily Cooldowns File Lock (.flock) và cơ chế Check-and-Reserve UUID
- **Vị trí áp dụng:** `core/target_lock.py`, `scripts/night_chain_reg_pipeline.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Nhiều worker chạy song song cùng đọc kho mail dư và cùng gán 1 email cho 2 máy khác nhau, gây trùng lặp và hỏng tài khoản reg.
- **Giải pháp chuẩn (Case Fix):**
  Dùng cơ chế **Check-and-Reserve có UUID Token** kết hợp file lock độc quyền (`.reg_daily_cooldowns.json.flock`). Worker phải reserve thành công trong lock mới được cấp phát target.

---

## PHẦN 4: DEVICE LOCK & ADB LIFECYCLE

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

### Case LOCK-03: Proxy sập -> Fail-Closed (Cấm chạy Direct IP)
- **Vị trí áp dụng:** `automation_core/vpn.py`, `python_runner/flows/feed_swipe_smoke.py`.
- **Nguyên nhân gây lỗi (Anti-Pattern):**
  Khi VPN `tun0` bị ngắt hoặc proxy bị die, script tự động chạy tiếp bằng mạng gốc (Direct IP), dẫn tới hàng loạt nick cùng dính chung 1 địa chỉ IP mạng nội bộ và bị TikTok gắn cờ hàng loạt.
- **Giải pháp chuẩn (Case Fix):**
  **Fail-Closed tuyệt đối:** Nếu VPN/Proxy mất kết nối, thực hiện tối đa 1 lần recovery cấp lại proxy + reboot máy. Nếu vẫn không có IP proxy hợp lệ -> Dừng ngay với 0 swipes (`final_status: blocked-vichanger-vpn`), cấm tuyệt đối lướt bằng Direct IP.

---

## CHECKLIST KIỂM TRA BẮT BUỘC TRƯỚC KHI CHỐT PHIÊN
- [ ] Task có liên quan đến Farm Automation (UI, Cron, Sync, Lock, ADB, Workbook...)?
- [ ] Nếu có: Đã cập nhật chi tiết Case Fix thực tế và Anti-Pattern vào `docs/uiautomator.md` chưa?
- [ ] Đã đồng bộ `docs/uiautomator.md` sang các repo liên quan chưa?
- [ ] Đã kiểm thử đối soát với dump XML thực tế và chạy test suite pass 100% chưa?
