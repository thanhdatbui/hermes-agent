---

name: tiktok-login-automation

description: TikTok login automation via ADB — inventory, login, 2FA, UI handling for both legacy (46.x) and new UI.

---



# TikTok Login Automation


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

## Overview



Automate TikTok login on Samsung Galaxy S7 (SM-G930F/S, 1080x1920) devices. Supports two paths:

1. **Reconcile script** (`scripts/reconcile_tiktok_accounts.py`) — inventory + login missing accounts

2. **Manual ADB flow** — fallback when reconcile script fails (UI mismatch, navigation issues)



## Prerequisites

- Python Runtime: Use venv `D:\Taadaa\python-envs\tiktok-reg-recovery\Scripts\python.exe` (đảm bảo `automation-core` được install editable `-e D:\Taadaa\automation-core --no-deps` và có `pillow` trong venv).
- ADB at `C:\Program Files (x86)\xiaowei\tools\adb.exe` (user's farm config)
- AdbKeyboard APK at `com.github.uiautomator/.AdbKeyboard` (install from `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\...\apks\com.github.uiautomator\00_base.apk`)
- Workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (columns: Máy, Tik, ID, PASS, 2FA, GMAIL, PASS MAIL, ..., device ID)
- Safe Workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
- Proxy Mapping: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
- Source runner: `D:\Taadaa\tiktok-luot nuoi acc`
- Login project: `D:\Taadaa\Tiktok_Reg`

## Canonical Reconcile Command

```bash
cd /d/Taadaa/tiktok-log-in
env -u PYTHONPATH "D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" scripts/reconcile_tiktok_accounts.py \
  --workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" \
  --machines <M> \
  --adb-path "C:\Program Files (x86)\xiaowei\tools\adb.exe" \
  --source-runner "D:\Taadaa\tiktok-luot nuoi acc" \
  --login-project "D:\Taadaa\Tiktok_Reg" \
  --login-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" \
  --proxy-mapping "D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx" \
  --allow-live-reconcile \
  --full-scope-takeover
```
*Lưu ý: Luôn chạy kèm `env -u PYTHONPATH` để tránh virtualenv của Hermes nạp chéo `PIL` gây lỗi `ImportError: cannot import name '_imaging' from 'PIL'`.*



## Project Architecture



```

login_runner/

├── cli.py              # CLI entry (--live mode)

├── executor.py         # Orchestrator: lock → preflight → login flow

├── live_adapter.py     # ADB device adapter (supports legacy + new UI)

├── totp_provider.py    # Workbook-backed TOTP challenge provider

├── account_inventory.py # Device inventory + workbook comparison

├── account_reconcile.py # Inventory → reboot → login → verify

├── models.py           # LoginJob, ExecutionResult, Step, JobStatus

├── contracts.py        # Protocol interfaces

├── dpapi_secret.py     # Windows DPAPI credential storage

└── device_lock.py      # Central machine/serial lock

```



## Code Architecture — `live_adapter.py`



`AdbKeyboardTikTokAdapter` implements `DeviceAdapter` protocol:

1. `open_tiktok()` — wake, force-stop, monkey-start, detect UI version

2. `choose_login_method()` — navigate to username form (legacy or new UI)

3. `submit_identifier()` — type username, tap continue

4. `submit_password()` — type password, tap login

5. `current_challenge()` — detect 2FA or other challenges

6. `submit_challenge()` — type 2FA code, tap continue

7. `current_identity()` — verify profile username matches submitted identifier



### New UI Detection



At startup, check for `AssistedSignInActivity` (Google sign-in popup). If present → dismiss with back key → set `_new_ui = True`.



### New UI Login Flow (TikTok 44.x / 46.x)

1. **Dismiss post-install consent popup** "Đồng ý và tiếp tục" — appears after app data clear. Swipe UP from bottom: `input swipe 540 1600 540 400 300`. Added in `_dismiss_consent_popups()` and `_start_tiktok_and_wait()`.

2. Dismiss Google sign-in popup if present (back key)

3. **Màn hình Đăng nhập Bottom Sheet (Logged-out Profile):**
   - Khi chưa có tài khoản nào đăng nhập, bấm vào tab "Hồ sơ" sẽ mở modal trượt đăng nhập `I18nSignUpActivity` (mặc định mở form Số điện thoại + nút "Tiếp tục với email/tên người dùng").
   - `is_auth_landing_screen` phải nhận diện cả 2 dạng: (1) `"dang ky tiktok"` + `"ban da co tai khoan"` / `"tiep tuc voi email"`, VÀ (2) `"dang nhap"` + `"tiep tuc voi email"`.
   - `ensure_login_entry_screen`: Nếu app đang ở auth landing sau khi bấm Profile hoặc dropdown fail, bypass ngay sang luồng chọn email (`choose_email_login`), không loop tìm dropdown/rv5 vô hạn.

4. **Bẫy Substring Match văn bản Điều khoản (Legal Disclaimer Trap):**
   - Dưới chân modal đăng nhập có đoạn điều khoản dài: *"Bằng việc tiếp tục với tài khoản có vị trí tại Việt Nam, bạn đồng ý với Điều khoản Dịch vụ..."*
   - Nếu `find_node_in_xml` tìm `"Tiếp tục"` / `"Đăng nhập"` bằng substring lỏng lẻo (`t_flat in v`), hàm sẽ match nhầm node điều khoản này (bounds lớn) thay vì nút bấm thật → click vào điều khoản làm mở WebView Điều Khoản Dịch Vụ.
   - **Fix bắt buộc:** Ưu tiên exact match trước partial match; với từ khóa ngắn (<15 ký tự), bỏ qua các node text dài (>50 ký tự) để tránh click nhầm disclaimer.

5. **From login screen ("Đăng nhập vào TikTok"), tap "Tiếp tục với email/tên người dùng"**

6. Enter username/email → tap "Đăng nhập" / "Tiếp tục"

7. Enter password → tap "Tiếp tục"

8. If 2FA: generate TOTP → submit → tap "Tiếp tục"

9. Dismiss post-login popups: "Cho phép truy cập danh bạ?" (tap TỪ CHỐI), "Kiểm tra bảo mật" (tap Đóng)



### Post-Login Privacy Policy (SparkActivity)



On TikTok 44.2.3, after successful login the app shows a mandatory privacy policy in a WebView (`com.bytedance.hybrid.spark.page.SparkActivity`). **UIAutomator cannot see buttons inside WebViews** — the "Agree" button is HTML-rendered. Scroll to bottom (10+ swipes) then tap bottom-center (y ≈ 1700-1850). If still stuck: BACK dismisses without accepting — account won't be fully activated. Known unresolved pattern on SM-G930W8.



### TikTok 46.x Bottom-Sheet Auth Landing & Email Icon Switcher (2026-08-19)

1. **Auth Bottom-Sheet khi thiết bị đăng xuất hoàn toàn (`I18nSignUpActivity`):**
   - Không có header/dropdown switcher. Mở app/tap Profile sẽ hiện modal trượt.
   - `is_auth_landing_screen` phải nhận diện `dang nhap` + `tiep tuc voi email`.
   - Bỏ qua bước mở dropdown switcher để vào thẳng form email.
2. **Màn hình gợi ý đăng nhập nhanh "Tiếp tục với tên @username" khi Thêm tài khoản:**
   - Khi bấm "Thêm tài khoản", nếu máy có cache/credential cũ, TikTok 46.x hiện nút to `Tiếp tục với tên @<username>` (`[132,1160][948,1340]`).
   - Nếu `@username` trùng khớp với nick cần login -> tap trực tiếp vào nút này để đăng nhập ngay (1-tap fast-path).
   - Nếu hiện popup "Hãy cùng kiểm tra bảo mật nhanh nhé" -> tap nút **Đóng** `(996, 923)` góc trên phải sheet, không bấm Tiếp tục.
   - Chi tiết: `references/tiktok46-continue-as-cached-account-suggestion-20260823.md`.
3. **Chống tap nhầm Text Điều khoản pháp lý ở chân trang:**
   - Dưới chân màn login có text điều khoản dài chứa chữ *"tiếp tục"* -> match substring sẽ tap nhầm `(540, 1794)`.
   - `find_node_in_xml` phải ưu tiên **Exact match** trước partial match; nút **ĐĂNG NHẬP** đen ở tọa độ `(540, 878)`.
3. **Nút tròn Icon Email `(233, 1693)` khi thêm tài khoản 2, 3...:**
   - Form thêm nick mở mặc định ở tab Số điện thoại; không có tab text Email ở trên.
   - Tap nút tròn icon phong bì ở góc dưới bên trái bounds `[161, 1621][305, 1765]` -> tâm **`(233, 1693)`** để mở ô nhập Email `[138, 566][942, 626]`.
4. **Fallback OTP sang Password & 2FA TOTP:**
   - Nếu màn OTP có nút *"Đăng nhập bằng mật khẩu"* `[96, 1119][703, 1236]` -> tap `(400, 1177)` để nhập mật khẩu TikTok.
   - Nếu đòi 2FA -> sinh TOTP từ cột `2FA` workbook và submit.
   - Chi tiết: `references/tiktok46-login-modal-and-email-button-20260819.md`.



### Đăng nhập Hotmail không 2FA qua OTP Outlook App (2026-08-22)

- Khi tài khoản Hotmail trong workbook `taikhoan_dat_v2_updated .xlsx` có `2FA: None`:
  1. Đăng nhập Hotmail vào app Outlook trước (`flows/login_outlook_one_machine.py`).
  2. Khi TikTok app yêu cầu xác minh OTP: runner fallback sang đọc mã từ Outlook app (`read_tiktok_otp_from_outlook_app` / `_read_magic_link_with_inbox_recovery`), nhập 6 số vào ô OTP và chuyển tiếp vào tài khoản.
  3. Sau khi login thành công, luôn chụp ảnh xác thực trên Account Switcher (`open_account_switcher` + `list_accounts`) để kiểm tra đủ số lượng nick trên máy trước khi release lock. Chi tiết: `references/reconcile-missing-2fa-hotmail-20260822.md`.

### Đăng nhập TikTok qua Gmail OTP & Bẫy Gom Thread Conversation (2026-08-28)
- **Bẫy gom thread:** Gmail gom nhiều email TikTok vào 1 conversation thread khiến đọc đầu thread lấy trúng mã cũ (ví dụ 1 tháng trước) -> báo sai OTP. Phải pull-to-refresh inbox, mở thread mới nhất, cuộn xuống đáy thread đọc mã mới hoặc tap nút "Đăng nhập" (Magic Link).
- **Phản hồi Account Banned:** Sau khi submit OTP, nếu TikTok báo `Tài khoản của bạn đã bị đình chỉ.` -> chụp ảnh screencap gửi user, dọn dẹp màn hình về Home và báo blocker để thay thế nick trong workbook. Chi tiết: `references/tiktok-login-gmail-thread-grouping-and-banned-handling-20260828.md`.

### Xác minh danh tính qua SparkActivity (WebView OTP) sau khi nhập mật khẩu (2026-09-01)
- Khi đăng nhập mật khẩu thành công trên thiết bị mới/máy nuôi, TikTok có thể chuyển tiếp sang WebView `SparkActivity` yêu cầu: *"Xác minh đó là bạn -> Email n***8@gmail.com -> Xác minh danh tính bằng cách nhập mã được gửi đến..."*.
- Màn hình này không phải native Android input form mà là WebView; đọc mã OTP từ Gmail qua `_try_get_otp_gmail_app`, tap ô nhập mã và gửi text OTP 6 số qua ADB để hoàn tất chuyển tiếp vào Profile.

- **CẤM TỰ Ý KẾT LUẬN "NICK DỰ PHÒNG" KHI THIẾU ROW TRÊN MÁY (User Rule 2026-09-01)**:
- **Xử lý khi thiếu nick trong Switcher (User Rule 2026-09-01, đính chính 2026-09-02)**: Khi máy thiếu nick so với kế hoạch nuôi (< 6 nick trên máy): BẮT BUỘC kích hoạt chạy `reconcile_tiktok_accounts.py` để đăng nhập nick thiếu vào thiết bị. TUYỆT ĐỐI CẤM tự ý đôn slot hay chuyển nick thiếu sang máy khác khi máy chưa full 6 nick. Chỉ áp dụng swap/re-map Excel khi máy ĐÃ ĐẦY ĐỦ 6 NICK và dính nick thừa ở slot phụ (7/8) để tránh logout/login churn. Chi tiết: `references/in-device-account-swap-and-restore-pass-pitfall-20260901.md`.
- **Bẫy Khôi phục Mật khẩu từ Hotmail/Gmail**: Cột PASS TikTok phải là mật khẩu TikTok (chữ hoa/số/ký tự đặc biệt), CẤM lấy mật khẩu mail ghi đè vào cột PASS TikTok khi restore workbook.
  - Toàn bộ các dòng từ Slot 1 đến Slot 6 của mỗi máy trong `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx` đều là **tài khoản thật theo lịch nuôi/ca nuôi** (Row 1..6 tương ứng các ca sáng/trưa/tối ngày lẻ/chẵn).
  - TUYỆT ĐỐI CẤM agent tự ý suy diễn hoặc kết luận nick chưa có trên máy là "nick dự phòng" để báo "đủ tài khoản". Khi máy thiếu bất kỳ row nào đã có ID trong workbook, BẮT BUỘC phải thực hiện flow đăng nhập bù cho đủ toàn bộ danh sách tài khoản quy định của máy.
  - **Bẫy trùng ID do HOA / thường (Case Insensitivity)**: Khi rà soát trùng ID (như `Samnga2403` vs `samnga2403`), BẮT BUỘC so sánh `.strip().lower()`. Tuyệt đối không để sót hàng trùng handle do bộ lọc Excel phân biệt chữ hoa/thường. Khi dọn hàng trùng, xóa sạch Cột 3..9 và giữ nguyên Cột 1, 2, 10 để bảo toàn cấu trúc 8 slot.
  - **Quy tắc Điều chuyển nick thay vì Logout/Login (Tránh chết nick/văng session)**: Khi máy thiếu nick theo lịch (vd: thiếu `janayerton71` ở Slot 5) nhưng trên máy thực tế đang đăng nhập sẵn nick khác (vd: `buithudung2011` từ đợt reg ở Slot 7): KHÔNG logout ra vào vòng vo trên máy thật. Ưu tiên đôn nick có sẵn lên Slot 5 trên Excel (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `TikN.xlsx`) và chuyển nick thiếu (`janayerton71`) sang máy khác đang trống slot để nuôi, giúp máy tiếp tục chạy ngay không rủi ro. Chi tiết: `references/account-reallocation-vs-logout-login-20260901.md` và `references/auto-reconcile-on-switcher-missing-20260902.md`.

### Đổi mật khẩu TikTok & Xác thực danh tính qua SparkActivity (2026-08-22)
- **Workbook Invariant**: Không hỏi lại thông tin email/pass mail đã có trong `taikhoan_dat_v2_updated .xlsx` (cột 6 `GMAIL`, cột 7 `PASS MAIL`). Khớp với `q***8@gmail.com` trên UI và tiến hành.
- **Xử lý dòng tài khoản trùng ID**: Dựa vào bộ 6 thuộc tính `(Máy, ID, Pass, GMAIL, PASS MAIL, 2FA)` để phân biệt dòng hợp lệ và dòng rác trước khi dọn dẹp.
- **Bẫy scope mặc định của `password_change.py`**: Hàm `freeze_targets` mặc định chỉ lọc pass kết thúc bằng `@Ks` hoặc `@hotmail.com`. Phải pass explicit row hoặc điều chỉnh selector khi chạy cho nick cụ thể.
- **Đích gửi OTP đổi pass TikTok**: TikTok gửi mã 6 số về email chính gắn với nick (`GMAIL`), không gửi về recovery Gmail `thanhdatbui1995@gmail.com`. Chi tiết: `references/tiktok-password-change-identity-verification-20260822.md`.

### Đổi Email liên kết TikTok sang Hotmail OAuth2 (2026-08-22)
- Khi Gmail cũ bị chết (Captcha bot / hết hạn phiên Google): vào `Thông tin tài khoản` -> `Email` -> `Thay đổi email`.
- **Cơ chế TikTok**: TikTok **không hỏi mật khẩu TikTok và không đòi OTP mail cũ** trên máy tin cậy; chỉ gửi OTP 6 số về Hotmail mới.
- **Lấy OTP Hotmail tự động**: Đổi refresh token qua `login.microsoftonline.com` lấy `access_token`, kết nối IMAP XOAUTH2 `outlook.office365.com` đọc OTP 6 số.
- **Quy tắc Cooldown 24h**: Sau khi đổi email xong, **CẤM** đổi mật khẩu ngay trong cùng phiên; ngâm 24h để tránh rủi ro bảo mật (Risk Engine).
- **XML-First**: Dùng ATX-Agent JSON-RPC port 7912 để click động các trường email, nút tiếp tục và nhập OTP. Cập nhật đồng bộ `taikhoan_dat_v2_updated .xlsx` và `gmail_clean_v2.xlsx`.
- Script triển khai: `D:\Taadaa\tiktok-log-in\scripts\change_tiktok_email_flow.py`. Chi tiết: `references/tiktok-change-email-oauth2-hotmail-20260822.md`.

### Lỗi Conflicting Serials trong Workbook do Cột Device ID dính Text Ngày (2026-08-28)
- **Triệu chứng:** `CONFIG_ERROR: machine N has conflicting serials in workbook` khi chạy `reconcile_tiktok_accounts.py`.
- **Nguyên nhân:** Cột 10 (`device ID`) trong `taikhoan_dat_v2_updated .xlsx` dính text ngày (`23/08/2026`, `2026-08-25`) làm `taikhoan_run_safe.xlsx` có nhiều serial trên cùng 1 máy.
- **Khắc phục:** `sync-safe-workbook.py` tự động lọc bỏ chuỗi regex ngày tháng và fallback về serial hex chuẩn. Chi tiết: `references/sync-safe-workbook-serial-date-filter-20260828.md`.

### Tài khoản bị TikTok Đình chỉ (Suspended/Banned) & Quy trình dọn dẹp (2026-08-28)
- **Nhận diện:** Màn hình OTP / Password báo `Tài khoản của bạn đã bị đình chỉ.` -> Gắn nhãn `account_banned`, chụp screencap bằng chứng.
- **Quy tắc vị trí row:** Khi báo cáo vị trí, luôn nêu rõ **Machine Slot (Row thứ N của Máy X)** kết hợp Excel Row và Tik folder.
- **Quy trình dọn dẹp TikTok vs Gmail (BẮT BUỘC PHÂN BIỆT RÕ):**
  - **Trên Excel:**
    - `taikhoan_dat_v2_updated .xlsx`: Xóa ID TikTok, Pass TikTok, 2FA về ô trống (None). **BẮT BUỘC GIỮ LẠI CỘT GMAIL và PASS MAIL** để script `Tiktok_Reg` (`_detect_clean.py`) nhận biết mail đã dùng, không gọi lại mail đó để reg TikTok mới.
    - `taikhoan_run_safe.xlsx` & `TikN.xlsx`: Dọn sạch slot ID TikTok tương ứng (`ID = None`, `Count = 0`).
  - **Trên thiết bị Android:**
    - CHỈ xóa/đăng xuất tài khoản TikTok trong app TikTok.
    - **TUYỆT ĐỐI KHÔNG XÓA TÀI KHOẢN GOOGLE/GMAIL KHỎI THIẾT BỊ** (trừ khi user chỉ đích danh yêu cầu xóa Gmail). Tài khoản Gmail phải được giữ lại trên máy để tiếp tục sử dụng.
  - Sau khi dọn dẹp, kiểm tra lại thiết bị về màn hình Home và release lock.



1. Navigate to Profile → open account switcher

2. Tap "Thêm tài khoản"

3. Tap "Bạn đã có tài khoản? Đăng nhập"

4. Tap "Sử dụng số điện thoại/email/tên người dùng"

5. Tap "Email/tên người dùng" tab

6. Enter username/password as above



### 2FA Handling



`WorkbookTotpProvider`:

1. Receives `LoginJob` + `SecretProvider`

2. Gets identifier from secret provider

3. Finds row in workbook matching `(machine, identifier)`

4. Reads 2FA column (TOTP secret, 32-char base32)

5. Generates current code via `pyotp.TOTP(secret).now()`



## Cross-repository handoff

For a live operator sequence that starts with a popup `OK`, then checks account inventory/login in this repo, and returns to `tiktok-luot nuoi acc`, follow the exact target/evidence/entrypoint rules in `references/cross-repo-ok-inventory-feed-handoff.md`. In particular: resolve one valid serial, never edit a malformed source workbook row, click only one verified `OK` node and recapture, treat `login_attempts=[]` plus no remaining device-missing accounts as “no login needed,” and use the feed runner's default preparation path when the device is on Launcher.

## Workbook Reading



Workbook uses column `device ID` (not `serial`). `SERIAL_HEADERS` in `account_inventory.py` must include `"device id"`.



Columns: Máy (machine number), Tik (slot), ID (username), PASS, 2FA, GMAIL, PASS MAIL, device ID (serial).



### Mail-source reconciliation before choosing a device



When the goal is to find a mailbox that has not yet been used for TikTok registration, do **not** infer status from `NGÀY TẠO` alone and do not treat an existing row in `taikhoan_dat_v2` as proof that the mailbox is registered. The canonical comparison is:



1. Read `gmail_clean_v2.xlsx`, sheet `Gmail Accounts`; this is the source inventory of mailboxes and contains the `số máy` assignment.

2. Read `taikhoan_dat_v2_updated .xlsx`, sheet `Tài Khoản`; build a normalized, case-insensitive set from its `GMAIL` column.

3. Candidates are rows present in `gmail_clean_v2` but absent from the `GMAIL` set in `taikhoan_dat_v2` (normalize whitespace/case).

4. Filter by domain only after the set difference, e.g. `@hotmail.com`; do not use a blank `NGÀY TẠO` as the primary criterion. A row can have an ID with a blank date, and `taikhoan_dat_v2` can omit a registered mailbox.

5. Resolve `số máy` → serial using `taikhoan_run_safe.xlsx` (`May` + `Device ID`) or `device ID` in `taikhoan_dat_v2`. Verify the mapping against live ADB before acting.

6. Never print passwords, password-mail fields, full email addresses, TOTP/2FA, or TikTok credentials. Report only machine number, masked address/domain, and counts.



See `references/mail-source-reconciliation.md` for the bounded procedure.



### Safe APK rollout across the farm



Installing an additional APK normally does not force-stop TikTok or ViChanger, but it consumes ADB bandwidth and Package Manager time and can affect live-farm throughput. Before rollout:



1. Inspect active farm processes and device-lock files; do not restart the gateway, proxy watcher, or unrelated workers.

2. Inventory online devices and query `pm path <package>` per serial.

3. Exclude every device that already has the package; never use an unconditional `install -r` for an all-device request.

4. Use the canonical Windows ADB path and a Windows path for APK arguments; MSYS `/d/...` paths may not be accepted by this ADB build.

5. Bound concurrency (e.g. 8 workers), log per-serial `OK`/`FAIL`, and verify the installed version afterward.

6. If a rollout process is interrupted, inspect and stop only that rollout's child processes before starting a corrected exclusion-aware pass. Do not kill scheduler/gateway/proxy processes and do not touch live device locks.



See `references/apk-rollout-exclusion-and-verification.md` for rollout pitfalls.



## Manual ADB Flow (fallback)



When reconcile script fails, do manual login per device:



```bash

ADB="C:/Program Files (x86)/xiaowei/tools/adb.exe"

SERIAL="<serial>"



# 1. Check current activity

$ADB -s $SERIAL shell "dumpsys window windows | grep mCurrentFocus"



# 2. Dismiss Google popup if present

$ADB -s $SERIAL shell "input keyevent 4"



# 3. Dump UI to find elements

$ADB -s $SERIAL shell "uiautomator dump /sdcard/window_dump.xml"

$ADB -s $SERIAL shell "cat /sdcard/window_dump.xml" | grep -oP 'text="[^"]*"'



# 4. Enable AdbKeyboard

$ADB -s $SERIAL shell "ime set com.github.uiautomator/.AdbKeyboard"



# 5. Type text

b64=$(echo -n "username" | base64)

$ADB -s $SERIAL shell "am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text $b64"



# 6. Tap at coordinates

$ADB -s $SERIAL shell "input tap X Y"



# 7. Generate TOTP

python -c "import pyotp; print(pyotp.TOTP('SECRET').now())"

```



## Evidence-Driven Live Recovery (bắt buộc)



### Live recovery: Chrome/Outlook foreground, focus theft, and marker classification



For a user-directed live recovery, **foreground and marker classification are separate gates**:



1. Capture the initial ADB focus/activity and screenshot. If Chrome/Outlook is foreground, bring TikTok back with `monkey -p com.ss.android.ugc.trill 1` **without force-stopping TikTok, clearing data, or sending input**, then immediately recapture focus/activity and screenshot.

2. A farm-side process can steal focus after TikTok was restored. Therefore verify focus **after the final screenshot/OCR**, not only immediately after launch. If Chrome/Outlook is foreground at that final check, relaunch TikTok once and recapture; do not claim TikTok is focused from an earlier capture.

3. Do not click signup controls based on the activity name alone. Click `Đăng ký`/the email continuation only when the current screenshot/XML explicitly proves a signup or method-selection surface. If the screen already shows OTP markers such as `Nhập mã ... 6 chữ số`, `mã xác nhận`, `resend code`/`Gửi lại mã`, classify as **OTP mode** and stop when the user forbids OTP entry/resend. If it shows `Kiểm tra hộp thư`, `liên kết`, `link`, or `Xác minh email`, classify as **magic-link mode**; never invent a numeric code.

 4. For Outlook/Hotmail magic-link recovery, inspect the live Chrome tab/mail DOM (CDP is acceptable for read-only extraction) and select the newest matching message by its visible timestamp/subject before using any href. Require the exact `tiktok.com/ucenter_web/deeplink/email_verification` anchor, save the selected href as evidence, then open it with `adb shell am start -a android.intent.action.VIEW -d <href>`; never click an unverified anchor or use an old OTP mail. The bounded recipe and evidence names are in `references/live-outlook-magiclink-view-intent.md`.

 5. When UiAutomator XML is unavailable or stale, screenshot evidence is still usable: save the screenshot, focus/activity output, OCR text, and the XML failure log. Never fabricate XML selectors or infer the marker from the activity name. If the evidence only proves an OTP screen and the next action is prohibited, report `FINAL_BLOCKED` with the exact marker and evidence path. If shell `uiautomator dump` returns a killed/non-XML result but the atx service is available, use the read-only atx endpoint `/dump/hierarchy` to obtain and save the XML; do not restart TikTok or alter app data.



Detailed command/evidence pattern: `references/live-recovery-focus-and-marker.md`.



### Ngưỡng chuyển từ worker sang guided recovery



- Cho worker chạy **detection/bounded handler** trước và theo dõi bằng `notify_on_complete`; không poll liên tục hoặc nạp toàn bộ log vào context.

- Dừng autonomous worker và chuyển sang guided recovery ngay khi có một trong các dấu hiệu:

  - UI signature chưa có handler đã được chứng minh;

  - UI dump treo, malformed hoặc trả payload non-XML;

  - cùng signature lặp lại sau một recovery có căn cứ;

  - worker chạy lâu nhưng không tạo proof tiến triển;

  - helper nội bộ loop/hang và cần external watchdog.

- Không giao Codex tự chạy lại full flow hàng giờ. Kill **toàn process tree**, không chỉ wrapper, rồi xác minh owner PID chết trước khi takeover orphan lock bằng central lock API.



### Guided loop



1. Giữ/takeover machine+serial lock cho toàn goal.

2. Trước mỗi action: foreground + screenshot + UI XML có watchdog + VPN/lock proof khi liên quan.

3. Classify màn hình/signature thật.

4. Thực hiện đúng **một action**: semantic selector/clickable parent trước; coordinate chỉ khi có screenshot/build/resolution evidence.

5. Recapture và ghi `state trước -> action/selector/tọa độ -> state sau`.

6. Không lặp cùng action nếu evidence không đổi.

7. Khi action thực tế đã qua, mới dispatch Codex đưa fix vào script + regression test; rerun đúng target/bước lỗi.

8. **KHÔNG tự mò tay khi đã có flow script (user rất tức — \"cứ tự mò chi vậy\")**: nếu flow script đã build xử lý từ bước X, khi tới bước X thì CHẠY SCRIPT (chạy runner lại), không tự bấm tay tiếp. Bấm tay là để CHẨN ĐOÁN và tìm tọa độ/semantic — sau khi tìm ra (vd tap tên yobi mở dropdown, kill atx để dump chuẩn), **phải handle ngay vào script + regression test rồi mới rerun**; không giữ kiến thức trong đầu rồi chạy tiếp bằng tay. User: \"chứ đụ mẹ nãy h m làm tay lúc qua đc sao m k handle lại script??? thế m làm tay nãy h công cốc à\".

9. **AI tự xử lý/recovery xong BẮT BUỘC ghi handoff ngay (user-ép rule)**: khi agent tự sửa (fix core, fix script, merge API, recovery máy) — dù chạy được hay kẹt — **phải ghi vào handoff.md ngay lúc xong từng bước**, không đợi cuối session. User: \"khi t hướng dẫn mày tự làm thì tới đâu ghi handle tới đó (cấm như hồi nãy tự làm xong đéo ghi handle, t nhớ t có ép rule làm tới chỗ nào kẹt vào tự xử lý = AI thì phải ghi handle khi recovery rồi mà)\". Kẹt tới bước nào thì **dừng lại báo user để hướng dẫn** (không tự loop vô hạn) — user: \"tới bước nào kẹt thì dừng lại để t hướng dẫn sửa\".



### Readiness marker timeout không đồng nghĩa VPN hỏng



Khi `acquire_device_lock()` timeout trong `wait_for_proxy_ready()` trước khi worker chạm TikTok:



1. Phân loại đây là lỗi **pre-lock readiness**, không phải lỗi login/UI.

2. Thu riêng `tun0`, `dumpsys connectivity`, foreground, screenshot, XML có watchdog và lock metadata.

3. Nếu `tun0` UP và Android VPN là `CONNECTED/VALIDATED`, marker có thể stale/missing. Reserve recovery bằng `bypass_proxy_readiness=True` chỉ cho bounded diagnosis/action; không dùng bypass cho login bình thường.

4. Consumer phải truyền `live_vpn_verifier` vào cả `acquire_device_lock()` và `soft_reboot_and_wait()`/post-reboot readiness. Verifier nên dùng primitive chuẩn `automation_core.preflight.check_android_vpn(..., required=True).allowed`, không tự regex lại proof.

5. Catch `RuntimeError`/`TimeoutError` phát sinh trước khi lease tồn tại và chuyển thành per-target recovery outcome; không để `future.result()` làm crash toàn batch.

6. Chỉ retry đúng target sau khi recapture chứng minh điều kiện readiness đã thay đổi. Đây mới là meaningful attempt 2.



Nếu foreground đang ở Vi Changer với `No LSPosed access !!!`, phân biệt modal với toast/snackbar bằng XML + screenshot. Chỉ tap exact semantic `OK` node khi XML chứng minh một control clickable duy nhất; recapture sau một action. Toast còn hiện nhưng không có modal không tự động là blocker nếu VPN live vẫn verified.



Chi tiết failure class và recovery ladder nằm trong `references/evidence-driven-reconcile-recovery.md`.



### XML hỏng không đồng nghĩa UI bị chặn



- Nếu screenshot + foreground + VPN vẫn khỏe, XML non-XML chỉ loại bỏ selector XML; **không được tự động kết luận `FINAL_BLOCKED`**.

- Kiểm tra screenshot-guided fallback đã từng chứng minh cho đúng app build và resolution. Dùng vision để xác định bounds, một tap/swipe mỗi vòng, rồi recapture.

- OCR/vision tự do có thể nhầm ký tự username (`i/r`, `z/2`, `v/y`). Khi proof là exact account set, đối chiếu candidate IDs đã scope từ safe workbook, crop/phóng lớn ảnh; nếu vẫn mơ hồ, chọn account dưới lock rồi verify Profile identity. Không tuyên bố exact match chỉ từ một OCR pass.

- `FINAL_BLOCKED` chỉ hợp lệ sau khi cả handler XML/instrumentation phù hợp **và** screenshot-guided handler có evidence (nếu tồn tại) đã cạn meaningful attempts, hoặc gặp hard stop thật.



Reconcile reboot làm watcher miss VPN vì lock collision là một failure class riêng. Nếu reconcile **cố ý giữ lock xuyên reboot**, không được thiết kế nó chỉ chờ watcher lấy cùng lock. Dùng post-reboot callback để parent runner gọi provider proxy hiện có dưới chính retained lock, verify ownership + `tun0` + Android VPN rồi mới tiếp tục. TikTok Profile logged-out phải được phân loại thành inventory rỗng, không phải account-switcher navigation failure. Chi tiết và contract: `references/retained-lock-post-reboot-proxy.md`; ladder takeover sau worker chết vẫn ở `references/evidence-driven-reconcile-recovery.md`; consolidated reproduction/testing notes ở `references/retained-lock-reconcile-recovery.md`. Session reference đầy đủ cho readiness-verifier propagation, TikTok 46.2.x UI layers, semantic anchor `sai`, core wheel integration và `pre_confirmed_xml` handoff: `references/reconcile-retained-lock-and-tiktok46.md`.



### TikTok 46.x overlay và switcher-anchor ladder



Khi Profile/switcher fail, xử lý từng lớp rồi recapture, không rerun full flow:



1. Feed tutorial `Vuốt lên để xem thêm` → vuốt lên đúng một lần.

2. Android `GrantPermissionsActivity` → dùng core detector `packageinstaller_permission`, chọn semantic `Từ chối`/Deny.

3. Google re-login sheet → đóng lớp trên cùng; bounded wait cho loading overlay trước khi đóng.

4. TikTok login modal → chỉ đóng để chẩn đoán Profile nền; nếu máy logged-out hoàn toàn, `is_auth_landing_screen` nhận diện qua `dang nhap` + `tiep tuc voi email` để vào thẳng luồng đăng nhập, không cố mở dropdown tài khoản.

5. Prompt `Lưu thông tin đăng nhập` → chọn semantic `Để sau`/Not now; generic Later không có save-login markers không được tap.

6. Profile logged-out cần đủ ba marker (`Hồ sơ`, `Đăng nhập vào tài khoản hiện có`, clickable `Đăng nhập`) mới được trả inventory rỗng.

- **Tránh tap nhầm văn bản Điều Khoản Dịch Vụ**: Trong `find_node_in_xml` / `node_has_target`, luôn ưu tiên node khớp chính xác (exact match) trước partial match để tránh chữ "tiếp tục" trong đoạn văn bản điều khoản pháp lý ở đáy màn hình bị click nhầm mở ra WebView Điều khoản Dịch vụ.
- **Chi tiết session Máy 4 (2026-08-19)**: Xem `references/reconcile-auth-landing-and-webview-terms-20260819.md`.



Trên TikTok `46.2.3`, override `1080x1920`, anchor tên/chevron có thể là clickable `android.widget.Button` với resource-id suffix `sai` (đã thấy bounds `[36,249][375,330]`). Đây là switcher anchor; person-plus góc phải là Add Friends và phải loại trừ. Sửa resolver trong shared `automation-core.tiktok.account_switcher`, thêm fixture regression, bump/build/install wheel; không thêm consumer coordinate fallback. Với core worktree isolated, chạy `PYTHONPATH=src pytest ...` để tránh vô tình test package venv khác, rồi xác minh resolver trên XML thật sau khi cài wheel.



Sau khi Profile được xác nhận, mọi bridge/provider phải giữ kết quả đó: `profile_xml = open_profile_root(...)` rồi `open_switcher(..., pre_confirmed_xml=profile_xml)`. Không gọi wrapper làm re-dump/re-navigation giữa hai bước; state có thể rơi lại về Home feed và tạo `SWITCHER_ANCHOR_AMBIGUOUS` giả. Áp dụng contract này ở cả consumer inventory bridge và provider login (`Tiktok_Reg`), với regression test xác minh exact kwargs.



Xem thêm `references/reconcile-guided-recovery-patterns.md` cho parent-lock proxy restore, readiness-verifier propagation, popup ladder và completion gate. Workflow live-check mail + cleanup CAPTCHA-die (máy 31/34 2026-08-07), core version reconciliation và policy cấm `pm clear`: `references/tiktok-reg-live-check-cleanup-20260807.md`. Chuỗi blocker máy 34 (login-surface preflight fix, code-freshness fix, ViChanger VPN restore, device-bound account): `references/tiktok-reg-machine34-chain-20260807.md`.



### Commit đúng worktree



Trước commit luôn chạy `git worktree list --porcelain`, `git branch --show-current`, `git status --short --branch` trong **path mà user gọi là “tree này”**. Stage file cụ thể; không stage dirty/untracked ngoài scope. Nếu commit nhầm tree, chuyển commit sang đúng branch bằng cherry-pick semantic (resolve handoff theo nội dung của target branch), rồi đưa pointer branch nhầm về commit trước bằng phương án không phá untracked/dirty state.



**Pitfall — `git add <file>` commit luôn CẢ đống thay đổi sẵn có của người khác (máy 34, commit `86c122d` 2871 dòng):** khi file đã có ~2870 dòng thay đổi chưa commit từ trước session (của người khác: `TARGET_INVENTORY_WORKBOOK`, hotmail_recovery imports, `_redacted_adb_command`...), `git add social_reg_v1.py` lấy TOÀN BỘ working-tree diff (kể cả line-ending CRLF↔LF churn) → commit phình 2871 dòng. Trước khi commit file đã modified sẵn: `git diff <file> --ignore-space-at-eol` để tách phần mình sửa vs phần người khác; nếu không tách được (cùng file) → **hỏi user** giữ nguyên (A) hay reset commit (B). Kiểm tra `git status` lúc session start để biết file nào đã dirty sẵn — tránh ngỡ mình tạo ra thay đổi của người khác.



**Pitfall — file UNTRACKED từ session start: `git add` → commit trọn file mới (không phải diff):** `run_tiktok_recovery_new_handler.py` nằm trong đống untracked lúc session start (chưa ai commit) → commit `f2188c0` hiện `1328 insertions + create mode` (cả file) dù tôi chỉ sửa 2 chỗ (`_version_lt`). `git show HEAD~1:<file>` → `exists on disk, but not in HEAD~1` xác nhận. Không phải lỗi nghiêm trọng (file đáng track) nhưng cần nhận biết: check `git log --oneline --all -- <file>` trước khi add để biết file đã từng commit chưa.



## Audit provider thực dụng (2026-08-07 — chain đã chạy, dùng lại được)



**⚠️ CẬP NHẬT 2026-08-09 — policy v6 phủ (AGENTS.md `Tiktok_Reg`, commit 2026-08-10):** Gemini **CẤM** trong audit route; Command Code **INACTIVE** (bỏ khỏi active route). Chain chuẩn v6: AG Claude (`ag/claude-opus-4-6-thinking/HIGH`, 1 route/task) → GPT review (`cx/gpt-5.6-terra-review|sol-review/HIGH`) → combo opencode-audit (9Router: `oc/nemotron-3-ultra-free` lead → big-pickle → longcat-2.0-free → ling-3.0-tiny-free) → `AUDIT_ALL_ROUTES_FAILED`. CẤM làm auditor/planner: `gpt-5.6-luna`, `cmc/*`, `opencode-free`/`oc/*`/`deepseek-v4-flash-free` (DeepSeek Flash = worker). opencode allowlist đổi liên tục — luôn đọc AGENTS.md hiện hành trước khi chạy. Phần hướng dẫn Gemini/Command Code bên dưới chỉ giữ làm lịch sử, KHÔNG dùng nữa.



Khi cần audit độc lập cho thay đổi (AGENTS.md: Gemini → OpenCode → Command Code → fresh Codex, 1 slot dừng ở verdict đầu tiên):



- **Gemini `invoke-gemini-9router-audit.ps1`**: `-RepoRoot`, `-PromptFile` (file, KHÔNG `-Prompt` text), `-OutputDirectory`. **ĐỪNG truyền `-ContextPath @(...)` qua bash** — PowerShell không nhận array từ bash (`syntax error near unexpected token '('`); bỏ ContextPath (prompt tự nêu path) hoặc gọi qua file .ps1. Model `gemini/gemini-3.6-flash` reasoning high. Fail phổ biến: exit 23 `Invalid JSON body` 400 (9router) — advance slot.

- **OpenCode `invoke-opencode-audit.ps1`**: `-Prompt` (text, dùng `$(cat file)`), **model phải nằm trong allowlist wrapper** — catalog đổi thường xuyên: lần này `opencode/deepseek-v4-flash-free` và `opencode/ling-3.0-flash-free` BỊ TỪ CHỐI (`OPENCODE_MODEL_NOT_ALLOWED: allowed models: ...nemotron-3-ultra-free, ling-3.0-tiny-free, longcat-2.0-free, north-mini-code-free`); nemotron trả `MODEL_UNAVAILABLE`; **`ling-3.0-tiny-free` CHẠY ĐƯỢC** nhưng model yếu → trả verdict thiếu/INCOMPLETE. **`longcat-2.0-free` (model mạnh nhất allowlist) chạy qua CLI trực tiếp:**

  ```bash

  PROMPT=$(cat prompt.md); timeout 900 opencode run --dir "D:\Taadaa\Tiktok_Reg" --agent taadaa-review --format json --title "audit-..." --model "opencode/longcat-2.0-free" "Read-only audit. Repository: <repo>. Request: $PROMPT Do not edit files or run commands. Return VERDICT/FINDINGS (file:line)." > report.jsonl 2>&1

  ```

  → **VERDICT: MINOR_FIXES** với findings file:line cụ thể (dead code, version gate `!=`→semver, regex case) — dùng được như audit gate.

- **Command Code `invoke-command-code-9router-audit.ps1`**: `#requires -Version 7.0` — **phải chạy bằng `pwsh` THẬT (PowerShell 7)**, `powershell` 5.1 và `~/.codex/shell/pwsh` (cũng 5.1) đều fail `ScriptRequiresUnmatchedPSVersion`. Kiểm tra `pwsh -Command '$PSVersionTable.PSVersion'` ra Major 7 mới chạy; máy này chưa cài PS7.

- **Codex fallback cuối**: `codex exec --sandbox read-only -c 'model_reasoning_effort="high"' "$PROMPT"` — nhưng dễ **hết quota OpenAI** (`You've hit your usage limit... try again Aug 12`) → không chạy được. Khi Codex hết quota → opencode longcat là lựa chọn sống duy nhất.

- **Đọc report opencode JSONL**: `--format json` → UTF-8, mỗi dòng 1 JSON, lấy message bằng `json.loads(line)['part']['text']`. Wrapper khác (`invoke-opencode-audit.ps1`) ghi **UTF-16 (null bytes)** — đọc bằng `open(p,'rb').read().decode('utf-16')` rồi regex `"text":"(.*?)"`. Verdict keywords có thể nằm giữa message (không phải cuối).

- **Audit fail (không verdict) KHÔNG chặn công việc**: khi cả ladder thử hết (Gemini 400, opencode model-unavailable, PS7 thiếu, Codex quota) → báo user, tiếp tục (audit = gate cho case khó, nhưng không thể chặn vô hạn khi provider chết). Findings từ audit INCOMPLETE vẫn áp dụng được (pkill -9 consumer, regex IGNORECASE).





**Root cause (user chỉ đúng, core 0.4.38 comment live-proven 2026-08-06 farm SM-G930F/W8):** atx-agent giữ `UiAutomationService` handle. Khi service wedged, `uiautomator dump` trả `Killed`/137 ("Bad file descriptor"). **Force-stop package KHÔNG release handle — phải kill atx-agent**, dump về E=0 ngay. `uiautomator dump` child cũng có thể wedge ("could not get idle state") → kill `uiautomator` process nữa.



**BẮT BUỘC `pkill -9` (SIGKILL), KHÔNG dùng `pkill` (SIGTERM) — phát hiện 2026-08-07 (máy 34):**

Một atx-agent wedged park trong `futex_wait_queue_me` (S-state) và **bỏ qua SIGTERM** — `pkill -f atx-agent` chạy "thành công" (exit 0) nhưng process KHÔNG chết → dump vẫn E=137 mãi, runner kẹt transport-recovery loop (log đứng, dump mới nhất vẫn `_before_`, atx PID đổi do watchdog restart). Toybox `pkill` nhận signal: `usage: pkill [-SIGNAL|-l SIGNAL] [PATTERN]`. **`pkill -9 -f atx-agent`** kill cứng → dump về E=0 NGAY (live-proven máy 34: SIGTERM E=137 kéo dài, SIGKILL → E=0 tức thì). Core `_recover_uiautomator` đã đổi sang `pkill -9` (0.4.43).



```

adb shell "pkill -9 -f atx-agent; pkill -9 -f uiautomator 2>/dev/null; am force-stop com.github.uiautomator; am force-stop com.github.uiautomator.test; uiautomator quit"

# dump thử lại → E=0

```

Lưu ý: `pkill -9 -f uiautomator` có thể trả "Operation not permitted" (app u0_a196, không root) — KHÔNG sao; kill atx-agent + `uiautomator quit` đã đủ giải phóng handle.



**Core version — ĐÃ RESOLVED (merge vào source, hết dilemma):**

- Core 0.4.38 (Tiktok-video dùng): `_recover_uiautomator` đã có `ATX_AGENT_PROCESS_MARKER` + `UIAUTOMATOR_PROCESS_MARKER` pkill — nhưng **KHÔNG có API cũ** `AndroidTransportRecoveryError`/`MissingVpnRecoveryError`/`recover_android_transport`/`recover_missing_android_vpn` mà `run_tiktok_recovery_new_handler.py` import → nâng core lên 0.4.38 làm **runner crash ImportError**.

- Core 0.4.32 (wheel trong pip cache): có đủ API cũ nhưng KHÔNG có atx kill.

- **END STATE (2026-08-07, user-mandated "đẩy lên core cho all repo"):** 4 symbol legacy + 2 result dataclass (`MissingVpnRecoveryResult`, `AndroidTransportRecoveryResult`) đã được **merge verbatim từ wheel 0.4.32 vào SOURCE** `automation-core/src/automation_core/device_recovery.py` → bump **0.4.41 → 0.4.42** (API cũ + expected_marker) → **0.4.43** (pkill -9 SIGKILL). Build bằng `python -m pip wheel . --no-deps -w dist` (Hermes venv KHÔNG có `python -m build` — `No module named build.__main__`), install `--force-reinstall --no-deps`, dọn dist-info cũ (chỉ giữ bản mới nhất — `importlib.metadata.version` trả bản CŨ NHẤT khi nhiều dist-info cùng tồn tại). Commits: `fc5d237` (expected_marker), `9561f3d` (legacy API merge), `a57ab2b` (pkill -9 + test update) trên nhánh `feat/hermes-cli-fallback`.

- **Pitfall — runner version gate:** `run_tiktok_recovery_new_handler.py` có `_require_runtime_core_version()` so `REQUIRED_CORE_VERSION` với `importlib_metadata.version('automation-core')` — upgrade core mà không bump gate → chết `AUTOMATION_CORE_VERSION_MISMATCH:expected=0.4.31;actual=0.4.42` NGAY lúc import (trước khi chạm device). Luôn bump `REQUIRED_CORE_VERSION` song song với wheel core trong cùng commit.

- **Pitfall — gate `!=` chặn cả core MỚI hơn (audit longcat P2, commit `f2188c0`):** gate cũ `if version != REQUIRED_CORE_VERSION` từ chối cả 0.4.44/0.4.45 (mục tiêu chỉ là chặn core cũ/stale). Fix: `_version_lt(actual, minimum)` (so sánh tuple `(major, minor, patch)` numeric) + `if _version_lt(version, REQUIRED_CORE_VERSION)` → chặn core cũ, cho phép patch mới. Test nhanh: `0.4.42<0.4.43` True, `0.4.44<0.4.43` False, `0.4.43<0.4.43` False.

- **Pitfall — test core cũ kỳ vọng `pkill -f`:** `tests/test_ui_dump.py` assert `["pkill", "-f", "atx-agent"]` — đổi code sang `pkill -9` phải cập nhật test song song (`["pkill", "-9", "-f", ...]`), nếu không canonical suite fail (2 test trong `test_ui_dump.py`: `test_dump_kills_wedged_uiautomator_child_*`).

- **Pitfall — pyproject.toml conflict marker:** khi bump version giữa lúc có stash/merge đè, TOML có thể bị `<<<<<<< Updated upstream`/`=======`/`>>>>>>> Stashed changes` → pytest chết ngay `Invalid statement (at line 7)` → sửa conflict giữ version mới rồi `git commit --amend` + `git push --force-with-lease` (đã làm).



**Sau khi pkill atx-agent, core báo `DEVICE_NOT_PROVISIONED`** vì atx-agent không tự restart: phải khởi động lại:

```

adb shell "nohup /data/local/tmp/atx-agent server >/dev/null 2>&1 &"   # atx-agent -d là SAI flag

adb forward tcp:7912 tcp:7912 && curl -X POST http://127.0.0.1:7912/uiautomator -d '{}'  # "Already started" → service chạy

```

Kiểm tra: `curl http://127.0.0.1:7912/uiautomator` → `{"running":true}`; `netstat -tlnp | grep 7912` LISTEN.



### Dump trả nội dung SAI (E=0 nhưng sai state) — không chỉ E=137



uiautomator dump có thể **thành công (E=0) nhưng trả nội dung CŨ/SAI**: máy đang ở profile `@yobi` nhưng dump ra feed ("Tây Ninh", "Bạn bè") → core `find_switcher_anchor` không thấy node "yobi" → `SWITCHER_ANCHOR_AMBIGUOUS` giả. Dấu hiệu: dump text KHÔNG khớp screenshot/`dumpsys activity` (mResumedActivity = profile mà dump ra feed). **Kill atx-agent vẫn hồi phục** (dump chuẩn lại ngay) — user: "uiautomator dump thì kill atx để xử lý đi".



**Fix A — `expected_marker` trong core (đã làm 2026-08-07, user chọn, ĐÃ ĐẨY LÊN SOURCE):**

- Core `automation_core/ui.py` `_dump_current_ui_unlocked` thêm param `expected_marker: str | None`. Trong `try_shell`, sau khi có text: nếu marker khớp (casefold, strip) KHÔNG có trong dump → `failure_signature="EXPECTED_MARKER_MISSING"` + gọi `_recover_uiautomator(adb, min(10, timeout), attempts, "expected_marker_missing_cleanup")` (kill atx + force-stop uiautomator) → return None để retry dump chuẩn. Truyền qua `dump_current_ui`/`capture_ui_xml` (kwargs).

- Consumer `Tiktok_Reg`: `get_ui_xml(device_id, deadline=None, expected_marker=None)` pass xuống `capture_ui_xml(..., expected_marker=...)`; `_SocialAccountSwitcherAdapter.dump_ui` → `get_ui_xml(self.device_id, expected_marker="hồ sơ")` (dump khi mở switcher phải chứa profile).

- **END STATE (session này):** patch đã đẩy lên **source** `D:\Taadaa\automation-core\src\automation_core\ui.py`, bump version **0.4.40 → 0.4.41** (expected_marker) → **0.4.42** (merge 4 legacy API từ 0.4.32 vào `device_recovery.py` — hết dilemma "không có wheel nào có cả 2") → **0.4.43** (`pkill -9` SIGKILL). Build wheel bằng `python -m pip wheel . --no-deps -w dist` (lưu ý `python -m build` KHÔNG có trong Hermes venv — `No module named build.__main__`), install `--force-reinstall --no-deps` vào `tiktok-reg-recovery`, dọn **dist-info lẫn lộn** (nhiều `automation_core-<ver>.dist-info` cùng tồn tại → `importlib.metadata.version` trả bản CŨ NHẤT; xóa hết chỉ giữ bản mới nhất), commit `fc5d237` + push nhánh `feat/hermes-cli-fallback`. **atx kill KHÔNG ảnh hưởng tài khoản** (chỉ kill process agent/UI handle, không đụng app data — user đã hỏi, đã xác nhận; đây là câu trả lời chuẩn cho lần sau).

- **Pitfall: pyproject.toml conflict marker** — khi bump version giữa lúc có stash/merge đè, TOML có thể bị `<<<<<<< Updated upstream`/`=======`/`>>>>>>> Stashed changes` → pytest chết ngay `Invalid statement (at line 7)` → sửa conflict giữ 0.4.41 rồi `git commit --amend` + `git push --force-with-lease` (đã làm).

- Các repo khác muốn hưởng: upgrade core ≥0.4.41 + truyền `expected_marker` ở nơi cần.

- Verified: ad-hoc 10/10 + pytest consumer 10/10 + core UI tests (test_ui_dump+circuit+state_machine) 31/31 + replay 26/26 + full core suite 225 pass/1 fail (fail = `test_startup` PRE-EXISTING, liên quan `startup.py` dirty sẵn — stash-verify trước khi quy kết patch).



**Consumer-side (vẫn giữ, double protection):** `_try_open_account_dropdown_once` gọi `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` + sleep 1.5 TRƯỚC `open_account_switcher` — đảm bảo dump chuẩn trước khi core tìm anchor. (Nếu consumer patch cũ còn `pkill -f` — đổi sang `-9`; SIGTERM vô dụng với atx treo futex.)



### Hook `adapter.coordinate_fallback(action)` — core đã hỗ trợ sẵn, consumer PHẢI implement (commit `687eb86`, máy 34)



Core `open_switcher` (account_switcher.py ~L679-680) khi anchor semantic/image đều unavailable sẽ gọi `adapter.coordinate_fallback("switcher")` để lấy tọa độ tap fallback. Nếu consumer adapter **KHÔNG implement hook này** → `point=None` → `SWITCHER_ANCHOR_AMBIGUOUS` dù máy THẬT đang ở profile (dump stale/treo khiến core không đọc được tên user). Đây là lý do pkill atx + expected_marker đều đã fix mà vẫn dính lỗi.



- **Fix đúng = consumer thêm primitive** (KHÔNG phá core — core đã define hook sẵn): `_SocialAccountSwitcherAdapter.coordinate_fallback(self, action=None)` trả `(540,150)` (tap tên user header mở dropdown, verified live) cho `action == "switcher"`, `None` cho action khác. Comment ghi rõ hook + tọa độ verified.

- **Test guard cũ phải đổi:** `tests/test_login_method_entry.py` từng assert `not hasattr(adapter, "coordinate_fallback")` (ý "consumer không override core policy") — nhưng hook là extension point core CHỦ ĐỘNG gọi → assertion lỗi thời. Đổi sang `assert hasattr(...)` + test 2 case: `coordinate_fallback("switcher") == (540,150)` và `coordinate_fallback("unknown") is None`. Audit opencode longcat bắt đúng P0 này (break test) — verify code thật trước khi sửa.

- **General hóa (2026-08-07, core-level):** plan đã audit MINOR_FIXES — thêm docstring contract `coordinate_fallback(action: str) -> tuple[int,int] | None` vào `open_switcher`/`open_account_switcher` (backward-compat: adapter không có hook = None = hành vi cũ) + unit test core (adapter có hook → gọi; không hook → vẫn SWITCHER_ANCHOR_AMBIGUOUS, không TypeError — core đã wrap `callable(evidence)`). KHÔNG refactor rộng.



### Classifier `_is_personal_profile_screen_xml` dương tính giả trên feed (2026-08-07, máy 34)



Root cause mới của `SWITCHER_ANCHOR_AMBIGUOUS` loop relaunch: KHÔNG phải dump stale — mà **`_is_personal_profile_screen_xml` nhận nhầm feed TikTok là profile** → `go_to_profile` log "✓ profile selected" dù máy vẫn ở feed → core `open_account_switcher` chạy trên feed → không thấy anchor → loop vô hạn. Triệu chứng: log `[2] Go to profile tab` → `profile selected` → `[3] Open account dropdown` → relaunch recovery → lặp; dump quanh đó là feed ("Tây Ninh"/"Bạn bè").



Các nhánh dương tính giả ĐÃ sửa (trong `_is_personal_profile_screen_xml` + `_has_profile_header_marker` mới):

- Nhánh `all(marker in flat for ["follower", "da follow", "thich"])` — **feed có bottom tabs "Đã follow"/"Thích"** → phải kèm `_has_profile_header_marker(xml)`.

- Nhánh `all(marker in flat for ["chia se video", "tai len"])` — **feed có nút "Chia sẻ"** → phải kèm header marker.

- `_has_profile_header_marker` (hàm mới): tên user profile phải là node có **`clickable="true"`** + **bounds y1 ≤ 300** (header region; creator/video names ở giữa màn y>1000) + không phải số thuần (`isdigit`) + không thuộc stopwords (`trangchu/cuahang/hopthu/hos/banbe/dafollow/dexuat/thich/...`); `@username` phải clickable. Node "Thanh Thượng Tiên" (creator name, clickable=false, y1=1466) không lọt.

- `_is_personal_profile_screen_xml` ưu tiên `_has_profile_header_marker` TRƯỚC `_is_home_feed_xml` (dump có thể còn sót feed-tab markers).



**ĐÃ FIX (2026-08-07, verify 5/5 ad-hoc + 10/10 pytest + diff clean, commit `86c122d`):** nhánh follower giờ khớp **node riêng** bằng regex per-node `^(?:[\d.,\s]*)?(?:nguoi dang follow|dang follow|followers?)$` (strip_accents + lower) — KHÔNG match substring trong toàn bộ text ("Đăng lại cho follower" của video feed không lọt).



**3 bài học bổ sung sau khi fix classifier (máy 34 run 20260807-182529 live-proven — đi xuyên cả flow: profile → dropdown → Thêm tài khoản → email → OTP):**

- **expected_marker "hồ sơ" VÔ DỤNG phân biệt feed/profile** — bottom tab "Hồ sơ" luôn hiện trên feed → marker pass dù dump là feed → core vẫn `SWITCHER_ANCHOR_AMBIGUOUS`. Marker phải là **tên user profile** (display_name từ `extract_profile_identity`, vd "yobi" — chỉ profile thật có). `_SocialAccountSwitcherAdapter.dump_ui` đổi sang `_profile_marker()`: đọc `extract_profile_identity(xml)` → display_name ≥3 ký tự làm marker; rỗng thì bỏ marker (dựa vào classifier core). Run 182529 qua dropdown với marker tên user.

- **Verify profile thật TRƯỚC core mở switcher:** `_try_open_account_dropdown_once` sau kill atx + sleep 1.5, loop 2×: `get_ui_xml` → `_is_personal_profile_screen_xml(xml_check)`; không phải profile → log `[account-switcher] not on real profile; re-tap profile tab` + tap `COORD["profile_tab"]` + chờ. Run 182529 log này ×2 rồi mới vào profile — cơ chế hoạt động.

- **Sau OTP-phase STOPPED, máy kẹt ở màn login TikTok** (`SignUpOrLoginActivity`): run kế fail `[02_profile]` vì tap profile tab không vào được từ màn login. Fix trước rerun: `input keyevent 4` ×2 (thoát login → SplashActivity → feed), verify dump có feed ("Tây Ninh") rồi chạy lại. Preflight preserve-login fix (mục Common Gotchas) KHÔNG đủ — máy kẹt login cần back tay trước khi rerun.



Chi tiết session (SIGKILL diagnosis transcript, legacy-API merge diff, version gate, pyproject conflict, verification evidence): `references/atx-sigkill-and-core-merge-20260807.md`.



**Pitfall — máy 34 dump "E=137/stale feed" dai dẳng mà pkill atx không ăn → reboot + dismiss LSPosed + đợi VPN mới hồi phục (máy 34 live 2026-08-07):** sau vài force-stop runner, máy 34 rơi vào trạng thái **dump luôn `E=137` (`Killed`) + `cat` trả nội dung CŨ (feed "Tây Ninh") dù màn thật profile** — kể cả đã `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` (cách thường thắng). Chuỗi hồi phục mạnh: **reboot → đợi boot_completed=1 → dismiss popup LSPosed `vn.vichanger.app` (nút `OK` — che màn, khiến app không idle) → đợi tun0 UP → mở TikTok → chờ splash/feed đứng yên ≥60-75s** → `uiautomator dump` về E=0 trả feed thật. Dấu hiệu nhận biết: dump E=137 + màn có popup LSPosed hoặc VPN chưa uplink. **Nội dung `/sdcard/wd.xml` cũ có thể KHÔNG đáng tin (stale) khi dump E=137/máy không idle** — luôn xác minh bằng screenshot (`screencap -p` + vision) trước khi tin dump nói gì. Node dump trả tọa độ cũ (vd 1857) cần đối chiếu bounds thật bằng screenshot.



### Skip-profile: máy ĐÃ Ở màn login → bỏ qua profile/dropdown (2026-08-07, máy 34 — commit `32af1ed`)



**Profile tab KHÔNG render trên một số máy (live-proven máy 34 SM-G930K, TikTok 46.x):** tap profile tab → splash → quay về feed (dump fail vẫn là feed "Tây Ninh"/"Bạn bè" dù log "profile selected"), kể cả NGAY SAU reboot với TikTok fresh. `profile selected` là dương tính giả của `is_profile_tab_selected` (tab selected + marker feed), không phải profile thật. Chỉ path thắng được chứng minh (run 182529: profile → dropdown → Add account → email → OTP) là khi máy **ĐÃ Ở màn login TikTok** (`SignUpOrLoginActivity`) — runner không cần profile.



**Fix `_skip_profile_nav` (đã commit `32af1ed`, sửa tiếp run sau):** đầu flow chính (sau `open_app`/`shot("01_open")`), `_initial_login_xml = get_ui_xml(device_id)`; nếu **chỉ `_is_login_method_surface_xml(_initial_login_xml)`** → `_skip_profile_nav = True` → bỏ qua `go_to_profile` → **rơi thẳng xuống `fill_email_and_next` (bước 7)** — KHÔNG return sớm, KHÔNG gọi `continue_email_signup_from_entry` (hàm đó CHỈ hợp khi `_post_auth_ui_state == "registration_entry"` — profile logged-out, KHÔNG phải màn login).



**⚠️ PITFALL — KHÔNG gọi `_has_email_form` trong flow module-level (đã crash `NameError: name '_has_email_form' is not defined`):** bản `32af1ed` ghi `if _is_login_method_surface_xml(...) or _has_email_form(...)` — nhưng `_has_email_form` là **nested function định nghĩa BÊN TRONG hàm khác (~line 3051)**, KHÔNG phải module-level → gọi ở flow module-level (line ~9288) chết `NameError: name '_has_email_form' is not defined` ngay preflight (`[gate] preflight_phase ... ERROR`), runner exit ngay 0 attempt. Bài học: trước khi tham chiếu 1 helper trong flow module-level, **verify hàm đó thuộc module scope** (`grep '^def _has_email_form'` — đầu dòng = module-level; thụt lề = nested → KHÔNG dùng). Chỉ dùng `_is_login_method_surface_xml` (module-level thật).



**Pitfalls quanh màn login:**

- `SignUpOrLoginActivity` **KHÔNG exported** — `am start -n com.ss.android.ugc.trill/...SignUpOrLoginActivity` → `Security exception: Permission Denial: not exported`. Không mở trực tiếp bằng intent được.

- Không logout acc đang login để vào màn login (mất session device-bound; acc đã ghi workbook nhưng phải đăng nhập lại sau). Hỏi user trước khi logout.

- Sau OTP-phase STOPPED, máy **kẹt ở màn login** → run kế fail `[02_profile]` (tap profile tab không ăn từ màn login). Fix trước rerun: `input keyevent 4` ×2 → SplashActivity → feed (verify dump có "Tây Ninh"), rồi chạy lại — lần này máy ở feed nên skip-profile không kích hoạt, nhưng preflight sẽ đưa về màn login đúng lúc.



### Lock orphan serial tự-block runner mới (2026-08-07, máy 34)



Runner crash trước để lại **CẢ 2 lock** `machine_<N>.lock.json` VÀ `serial_<SERIAL>.lock.json` (cùng PID chết). Runner mới: dọn được cái này nhưng vướng cái kia → `DEVICE_LOCKED` FINAL_BLOCKED chỉ sau **~39s** (fail rất nhanh, ledger blocker = lock path + pid). Gỡ 1 cái KHÔNG đủ — phải dọn CẢ 2 loại. Verify PID chết bằng **`wmic process where "ProcessId=N" get ProcessId,CommandLine`** — `tasklist //FI "PID eq N"` có thể trả RỖNG dù process còn sống (silent fail trên git-bash), gây bỏ sót. Runner mới còn có thể TỰ TẠO lock serial (pid chính nó) rồi vẫn bị block bởi lock machine_ cũ → xóa cả 2 trước khi rerun.



## CẤM TUYỆT ĐỐI `pm clear` TikTok (policy — user rất tức)



**KHÔNG BAO GIỜ `pm clear com.ss.android.ugc.trill`** để đăng xuất/đổi account — làm mất toàn bộ account/session đang login trên máy (sự cố máy 34 2026-08-07: mất account người khác trên device, user quở trách). Đăng xuất chỉ qua UI logout trong app hoặc hỏi user. Policy đã ghi vào AGENTS.md 6 repo: `Tiktok_Reg`, `add mail khoi phuc`, `Hotmail`, `gan-proxy`, `automation-core`, `Tiktok-video`.



**Account TikTok gắn cứng device (device-bound):** `@handle` đang login VẪN CÒN sau `pm clear` + xóa `android_id` + `pm clear com.google.android.gms` — TikTok nhận diện device qua fingerprint firmware-level (IMEI/serial/keystore), không xóa được bằng adb. Khi gặp máy login sẵn account lạ (không trong workbook): KHÔNG clear data, KHÔNG factory reset khi chưa hỏi user — báo user (có thể login thêm account qua Add account, hoặc user tự xử lý).



## Live-Probe Classifier Phải Khớp Repo `add mail khoi phuc`



`_gmail_account_live_probe` trong `social_reg_v1.py` dùng classifier riêng — dễ **bỏ sót identity-verification gate** → trả `NORMAL_ACCOUNT` sai trong khi mail thực tế CAPTCHA-die. Flow chính chủ (`run_add_recovery.py` repo `add mail khoi phuc`) detect đúng: "Xác minh danh tính của bạn" / "Để bảo mật tài khoản của bạn, Google cần xác minh danh tính" / "verify your identity" → `IDENTITY_BLOCKER` → CAPTCHA-die → xóa mail. Marker đã thêm: `xac minh danh tinh cua ban`, `de bao mat tai khoan cua ban`, `verify your identity`, `xac minh thong tin de tiep tuc` → `GoogleLiveState.IDENTITY_BLOCKER`. Khi nghi ngờ, chạy thẳng flow repo add mail: `rar.check_google_live_with_core(device, gmail, pass)` — đừng tin probe consumer nếu kết quả khác add-mail repo.



**Cleanup CAPTCHA-die đúng workflow:** `rar.cleanup_blocked_captcha_account({'gmail': ...}, so_may, reason)` từ repo add mail — xóa khỏi máy (`remove_blocked_google_account_from_device` qua Gmail → device accounts → XOÁ TÀI KHOẢN) + xóa khỏi `gmail_clean_v2.xlsx` (`backup_delete_account_from_workbook` + verify) + xóa khỏi `_clean_targets.json`.



**Bug `MACHINE_DEVICES.get(so_may)` trong add-mail repo:** fallback hardcoded map keys là **int** (`31: ...`) nhưng `cleanup_blocked_captcha_account` truyền `so_may='31'` (string) → `get('31')` = None → device=None → core fail `DEVICE_NOT_PROVISIONED` giả. Fix: `MACHINE_DEVICES.get(int(so_may)) if str(so_may).strip().isdigit() else MACHINE_DEVICES.get(so_may)`. Signature lỗi: log "Không xác định được account đích trong dumpsys account" dù account vẫn còn trong dumpsys.



### Bước 07 `fill_email_and_next`: giữ email khi màn magic-link verify ĐANG CHỜ SẴN (2026-08-07, máy 34, run 20260807-235541)



**Gap đã fix:** máy có thể ĐANG Ở SẴN màn magic-link verify khi bước 07 bắt đầu (chưa submit email nào trong run): "Kiểm tra hộp thư của bạn" + "Gửi lại email sau N giây" + "Đăng nhập bằng mật khẩu". Trước fix, `fill_email_and_next` chỉ check màn nhập email (`wait_for_text(["Email hoac TikTok","Email","TikTok ID"])`) → fail → log "✗ Khong thay man nhap email" → continue → bỏ qua email → cuối run báo SAI "Tat ca N email da co TK TikTok".



**Pattern chung (áp dụng cho mọi bail-out "không thấy màn X"):** TRƯỚC khi bỏ qua/continue vì không thấy màn mong đợi, lấy XML hiện tại → `strip_accents(xml).lower()` → gọi helper chung `_classify_after_continue_flat(flat)` (KHÔNG duplicate list marker). Nếu = `verify_email_pending` → log "CHUA co TK, TikTok dang cho xac minh magic link" → `return (em, pw, dob)` → bước 7c `handle_tiktok_email_otp` mở mail → bấm link. Ngoại lệ: email đã có TK trong tracking (`_mailbox_key(em) in used_emails`) → vẫn bỏ qua như cũ.



**Hai nhóm marker (commit 6615ac4, priority REAL_OTP TRƯỚC — màn OTP login thật thường kèm text "Kiểm tra email"):**

- `REAL_OTP_LOGIN_HINTS` ("xac minh email", "nhap ma", "gui lai ma", "resend code", "ma xac nhan", "ma xac minh", "verification code", "enter the code", "sent a code") → `registered_otp` = email ĐÃ có TK, login bằng OTP.

- `MAGIC_VERIFY_HINTS` ("kiem tra email", "kiem tra hop thu", "check your email", "check email", "gui lai email", "resend email") → `verify_email_pending` = email CHƯA có TK, TikTok gửi magic link xác minh đăng ký.



**Tests:** `tests/test_login_magiclink_classify.py` (8 cases: classify 5 + fill_email_and_next 3: magic-verify đang chờ → giữ email; resend-email-only → giữ email; màn thường → vẫn bỏ qua + lưu fail screen). UI.md entry: `tiktok-reg-magiclink-verify-step07-entry-20260807`. Chi tiết session (XML fixtures, code line, verify evidence): `references/step07-magiclink-verify-entry-20260807.md`.



**Verify/commit cho repo này:** file CRLF — sau patch phải check 0 LF-only (`python -c` đếm `\r\n` vs `\n`), `git diff --check` sạch, pytest đúng interpreter:

`PYTHONPATH="D:\Taadaa\python-envs\tiktok-reg-recovery\Lib\site-packages;D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail" "D:\Taadaa\python-envs\tiktok-reg-recovery\Scripts\python.exe" -m pytest tests/test_login_magiclink_classify.py tests/test_detect_after_continue.py -q -p no:cacheprovider`



**Tooling:** `search_files` đôi khi trả `rg: IO error` với path `D:\...` trên git-bash → fallback `rg -n "pattern" -g '*.py' .` qua terminal (không phải lỗi repo).



### Tap thủ công magic link trong Gmail app: nút đỏ "Xác minh email" (máy 34, 2026-08-08 — flow user chỉ + pixel-scan)



**Flow chuẩn (user chỉ — "kéo xuống dưới cùng của mail đó, có nút hiển thị văn bản được trích dẫn, nhấn vào r kéo hết xuống dưới cùng ms có nút đỏ xác minh email"):**

1. Mở thread "Hoàn tất đăng ký bằng cách xác minh email" → **kéo xuống CUỐI THREAD** (Gmail group mọi mail TikTok cùng thread; mail mới nhất nằm cuối).

2. Mail mới nhất hiển thị link xanh **"Hiển thị văn bản được trích dẫn"** (Show quoted text) — TAP link ĐÚNG CỦA MAIL MỚI NHẤT, không phải link của mail cũ (mỗi mail có link riêng; tap nhầm mail cũ → không hiện nút đỏ).

3. Link chuyển thành "Ẩn văn bản được trích dẫn" → **kéo xuống HẾT** → nút đỏ **"Xác minh email"** hiện.

4. Tap nút đỏ → focus đổi sang TikTok `SignUpOrLoginActivity`.



**Nút đỏ TRONG Gmail app LÀ TAP ĐƯỢC** (HTML link thật, KHÔNG phải image — nghi ngờ ban đầu sai). Vấn đề chỉ là TỌA ĐỘ.



**⚠️ vision_analyze ước tọa độ nút đỏ SAI liên tục** (báo (540,414)/(540,594)/(540,871) qua các lần — thực tế đúng là **(538,788)**): vision mô tả nội dung tốt nhưng coordinate không đáng tin cho button nhỏ. **Dùng pixel color cluster scan** (script: `references/gmail-magiclink-tap-manual-20260808.md`): quét 1080x1920, pixel TikTok-red (`r>180, g<120, b<130`), cluster hàng y liền nhau (gap>20 tách cluster) → center (538,788). Tap theo pixel-scan ăn NGAY; tap theo vision ăn 50/50.



**Link hết hạn 20 phút** ("Liên kết có hiệu lực trong 20 phút"). Khi TikTok hiện lại "Kiểm tra hộp thư" sau khi bấm link cũ = link hết hạn → **tap "Gửi lại email" (540,1350)** trên TikTok → chờ ~15-20s (cooldown giữa các lần gửi ~46-60s) → vào Gmail → thread → kéo cuối → link MAIL MỚI NHẤT.



**⚠️ Sau khi tap link, TikTok HIỆN LẠI màn "Kiểm tra hộp thư của bạn" KHÔNG có nghĩa verify fail** — verify có thể ĐÃ thành công (màn này là trạng thái chờ cũ). Kiểm tra: `am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.main.MainActivity` → profile account mới (banner "Hoàn tất hồ sơ của bạn", follower=1, chưa avatar, username tự đặt vd `@yobi1965`). Splash có thể kẹt vài giây rồi mới vào profile.



**Outlook/Hotmail KHÔNG có magic-link guard — gap STT30 2026-08-11 (audit read-only đã xác nhận, implement CHƯA tồn tại):** `prefer_magic_link` trong `handle_tiktok_email_otp` chỉ truyền sang Gmail reader; `_try_get_otp_outlook_cdp`/`_try_get_otp_browser` không nhận flag và **KHÔNG có timestamp/freshness check** (Gmail thì có `_gmail_timestamp_is_recent_after`) → trả mã 6 số ĐẦU TIÊN bất kỳ trong DOM/UI (thường là code CŨ của mail OTP login lần trước trong cùng thread Outlook) → `enter_otp_code` vào màn magic-link "Kiểm tra hộp thư của bạn" (không field OTP) → `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK`. **Label NÀY CHƯA TỒN TẠI trong code** (grep = 0; raise hiện tại là `[otp-enter] TikTok OTP screen unavailable...` / `TIKTOK_REGISTRATION_RESTART_REQUIRED`) — cần định nghĩa mới. `enter_otp_code` guard (L10215) thiếu "kiem tra hop thu"/"gui lai email" nên màn magic có chữ "Xác minh email" lọt qua substring "xac minh" (và `_post_auth_ui_state` L4419 cũng trả `otp_required` cho "xac minh email") → otp_nodes rỗng → blind tap (540,900) + Enter. Fix tối thiểu đã audit APPROVED (kèm điều kiện): propagate `prefer_magic_link`+`not_before` qua 2 reader; magic mode **CẤM trả/enter numeric**; `enter_otp_code` fail-closed raise `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK` trước mọi tap; newest-mail timestamp evidence ≥ not_before trước khi tap link; **CẤM CDP JS click** (navigate tab Chrome sang TikTok web, bypass deep-link app — chỉ UI semantic tap + `_return_to_tiktok_after_magic_link`); Outlook gom thread = mail mới nhất nằm CUỐI, không `find_text_tap("TikTok")` mở mail (mở row đầu = mail cũ). Execution path/test cases/rủi ro đầy đủ: `references/outlook-magiclink-gap-stt30-20260811.md`.



**⚠️ Gmail swipe NGANG = archive mail (user cảnh báo — "m swipe ngang ms lỗi")**: chỉ swipe DỌC khi cuộn mail; swipe ngang làm archive mail đang mở/nổi bật. Nếu archive nhầm mail mới nhất → user gỡ qua "All mail"/Undo (báo user, đừng tự mò).



**Workflow rule (user hỏi "nãy h làm tay có ghi handle lại k thế")**: làm tay xong flow này → **ghi tọa độ/flow vào script NGAY** (nhắc lại rule #8 Guided loop): `_try_get_otp_gmail_app` nên thêm handler pixel-scan nút đỏ khi text-match không thấy — không giữ kiến thức trong đầu rồi chạy tiếp bằng tay.



Chi tiết session (pixel-scan script, tọa độ từng bước, timeline resend/expiry): `references/gmail-magiclink-tap-manual-20260808.md`.



## Live OTP recovery: identity, focus, and fail-closed gates



For a user-directed OTP recovery after a magic-link or signup transition, treat the

mailbox and TikTok as two independently verified targets. The Outlook URL alone is

not sufficient proof of mailbox identity: a preserved Chrome session can show a

signed-in or login surface for a different Hotmail account while still satisfying a

weak inbox/URL predicate. Before selecting or reading a code, require the target

mail identity from visible UI/XML/DOM evidence (masked account identity or exact

source-row match) and save that proof. If the identity is absent, conflicting, or

only inferred from `outlook.live.com/mail`, stop with `FINAL_BLOCKED`; do not use the

first six-digit candidate.



Use this bounded sequence:

1. Capture TikTok focus/activity and screenshot; verify the expected OTP markers,

   not only `CommonFlowActivity`.

2. Open the existing Outlook tab/session, perform one real pull-to-refresh, and

   recapture. Choose only a TikTok row proven newest by timestamp/order evidence;

   exclude magic-link mail and previously rejected/known-old codes.

3. Open that row and save the message XML/screenshot. Extract the code only from

   the selected newest message. Never fall back to a background DOM scan or a

   generic six-digit match when newest-row or identity evidence is missing.

4. **Immediately before typing**, restore TikTok and recapture focus/activity/XML.

   Require `com.ss.android.ugc.trill` foreground plus the OTP markers and an

   available input node. Do not call `enter_otp_code` while Chrome, Gmail,

   RecentsActivity, Play Store, or any other overlay is foreground.

5. Type/submit once, then recapture focus/activity/XML and save the post-submit

   screenshot. Count success only when the OTP screen transitions to a verified

   post-OTP state (for example password-required/registration continuation) or a

   handler emits an explicit accepted result. A missing `otp-enter`/accepted

   proof, a lost `CommonFlowActivity`, or an overlay after mailbox handoff is

   `OTP_INPUT_UNVERIFIED` → `FINAL_BLOCKED`, not success.



Do not try to recover the original OTP screen by launching an exported-looking

component, clearing TikTok data, or rerunning the full signup. If state has changed

or system overlays take focus, preserve artifacts and stop; no resend spam, no old

code reuse, and no password entry unless separately scoped. Report briefly in

Vietnamese with status, final focus, artifact directory, whether OTP entry was

verified, and that password/code values were redacted. Keep repository/workbook

scope read-only when the request says live recovery only.



Session detail and artifact checklist: `references/live-otp-focus-and-mail-identity-20260812.md`.



## Common Gotchas



- **CẤM HỎI XIN OTP HOTMAIL KHI ĐÃ CÓ CƠ CHẾ ĐỌC TỰ ĐỘNG (User Rule 2026-09-02)**: Khi TikTok yêu cầu mã OTP gửi về `@hotmail.com`, hệ thống đã có sẵn 2 cơ chế đọc tự động qua `hotmail_provider.py`: (1) qua Outlook App trên máy (`read_tiktok_otp_from_outlook_app`), và (2) qua Graph API / XOAUTH2 (`read_tiktok_otp_from_graph_token`). TUYỆT ĐỐI CẤM dừng lại hỏi xin user mã OTP khi đang chạy tự động. Chi tiết: `references/automated-hotmail-otp-and-gmail-livecheck-20260902.md`.
- **Bỏ hoàn toàn ViChanger VPN & Quy trình Upload Avatar UI mới (2026-09-02)**: Farm đã chuyển 100% sang Wi-Fi proxy MikroTik/Singbox router level, cấm các script bắt buộc ViChanger app trên máy Android. Chi tiết & quy trình Upload Avatar UI mới / Thẻ onboarding: `references/tiktok-avatar-upload-ui-flow-and-vichanger-deprecated-20260902.md`.
- **Gỡ bỏ ViChanger VPN & Modal Lưu và Đăng Avatar (2026-09-02)**: Farm chuyển sang MikroTik/Singbox Wi-Fi proxy, CẤM script ép kiểm tra `require_android_vpn` hay ném lỗi `VICHANGER_VPN_NOT_CONNECTED`. Khi up avatar, sau khi tap `Lưu` `(792, 1794)` ở màn hình Cắt BẮT BUỘC tap tiếp nút đỏ `Lưu và đăng` `(540, 1764)` trên modal thông báo công khai thì avatar mới thực sự lưu. Kiểm tra Gmail live siêu tốc qua `checkmail.live` CDP port 9222. Chi tiết: `references/vichanger-removal-and-modal-save-avatar-20260902.md`.
- **TikTok 46.x Avatar Upload & Switcher Anchor Lệch Trái (2026-09-02)**: Xem chi tiết luồng Avatar, xử lý bẫy cuộn scan video baseline, tọa độ switcher lệch trái `(130, 290)` và hook `coordinate_fallback` trong `references/tiktok46-avatar-upload-flow-and-left-aligned-profile-switcher-20260902.md`.
- **Bẫy Mật khẩu Placeholder do Reg qua OTP Hotmail Graph API (Passwordless Flow) & Giải pháp Khởi tạo Mật khẩu qua Web Chrome (2026-09-02)**:
  - Khi nạp lại các tài khoản reg qua luồng Hotmail OTP (vd `djricnvy2ez`, `lyndiaschles21`), nhập mật khẩu từ workbook báo `Mật khẩu sai` (`id/i7f`).
  - **Nguyên nhân:** Nick reg qua OTP Graph API không qua bước tạo pass (`[pw] Không có màn nhập password → KHÔNG lưu pass (để trống)`). Pass trong Excel chỉ là chuỗi random placeholder sinh trước khi chạy, nick chưa từng có pass TikTok thật.
  - **Bẫy Xác minh Chéo trên App (Cross-Account Identity Trap):** Nếu thực hiện "Quên mật khẩu" trên App TikTok đang có sẵn các tài khoản khác trong Switcher, TikTok sẽ chặn bằng màn hình "Xác minh danh tính: Xác minh đó là bạn" và ép nhập OTP từ email của tài khoản khác đang active trên máy (vd: `l***3@gmail.com`).
  - **Giải pháp Chuẩn qua Web Chrome:** Mở Chrome vào `https://www.tiktok.com/login/phone-or-email/email` -> "Bạn quên mật khẩu?" -> "Email" -> nhập email Hotmail -> đọc OTP XOAUTH2/IMAP -> chuyển thẳng vào `tiktok.com/login/reset/password` để đặt mật khẩu mới khớp chuẩn với cột `PASS` trong Excel mà không bị chặn chéo danh tính. Chi tiết: `references/passwordless-account-password-creation-via-web-20260902.md` và `references/passwordless-reg-placeholder-pass-pitfall-20260902.md`.
- **Avatar Batch Upload & Switcher Fallback (2026-09-02)**: Xem `references/avatar-batch-and-switcher-fallback-20260902.md` (MaxParallel 40, profile scroll drift fix, crop dialog layout & coordinate_fallback hook).
- **Bẫy lỗi `VICHANGER_VPN_NOT_CONNECTED` do thiết bị mất kết nối ADB (2026-09-01)**: Khi `reconcile_tiktok_accounts.py` báo `VICHANGER_VPN_NOT_CONNECTED` hoặc `LIVE_VPN_NOT_READY`, luôn kiểm tra `adb devices` trước. Nếu serial không có trong danh sách, nguyên nhân là mất kết nối ADB/phần cứng (`DEVICE_NOT_FOUND`), không phải lỗi cấu hình VPN. Chi tiết: `references/reconcile-vpn-not-connected-vs-hardware-disconnect-20260901.md`.
- **Fast-Login Cache ("Chào mừng bạn trở lại") & Xử lý Lỗi TOTP "Nhập mã hợp lệ" (2026-09-02)**: Khi máy hiển thị danh sách nick cũ trong màn fast-login ("Chào mừng bạn trở lại" khi bấm Thêm tài khoản), tap trực tiếp vào dòng `@username` để đăng nhập/khôi phục session tức thì mà không cần qua form email/password. Nếu TOTP báo đỏ `Nhập mã hợp lệ` (`id/i7f`), xóa sạch ký tự cũ bằng `keyevent 67`, sinh TOTP mới và submit `(540, 1806)`. Chi tiết: `references/tiktok-multi-account-fast-login-and-totp-resync-20260902.md`.
- **Quy trình Kiểm tra Siêu Tốc Live Gmail khi Timeout OTP (2026-09-02)**: Khi TikTok login bị timeout chờ mã OTP Gmail (`BLOCKED_GMAIL_OTP_TIMEOUT`), không tự ý kết luận mail chết. Mở Chrome CDP port 9222 (`C:\Users\Kibe\AppData\Local\hermes\browser_profile`) gọi `checkmail.live` kiểm tra trong 1-2s: nếu Gmail **LIVE** -> tiếp tục luồng đăng nhập (F5 kéo refresh hộp thư); nếu **DIE** -> báo cáo và thực hiện dọn dẹp thay thế nick. Chi tiết: `references/tiktok-login-gmail-otp-timeout-and-live-check-rule-20260902.md`.
- **Upload Avatar & Xử lý Màn hình Crop / Nút Lưu Story (2026-09-02)**: Khi upload avatar, sau khi scan video phải scroll về đỉnh Profile để thấy nút bút chì `(849, 552)`; tại màn hình Crop uncheck story `(84, 1590)`, tap Lưu `(792, 1794)` và Lưu và đăng `(540, 1764)`. Chuyển account qua anchor `(140, 300)`. Chi tiết: `references/tiktok-avatar-upload-ui-recovery-and-crop-save-20260902.md`.
- **CẤM TỰ CHẾ "NICK DỰ PHÒNG" KHI THIẾU INVENTORY**: Mọi row có ID TikTok trong `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx` (Row 1..6) đều là tài khoản thật (Row 5 & 6 là ca 3 ngày lẻ/chẵn theo lộ trình warmup). Tuyệt đối không tự suy diễn "nick dự phòng" khi máy thiếu nick so với Excel; thiếu bất kỳ row nào BẮT BUỘC phải login bù. Chi tiết: `references/spark-identity-verification-and-inventory-enforcement-20260901.md`.
- **ĐIỀU CHUYỂN SLOT THAY VÌ LOGOUT/LOGIN VÒNG VO (User Rule 2026-09-01)**: Khi máy đã đầy 6 nick và chứa sẵn 1 tài khoản thật ở slot phụ (7/8), cấm logout tài khoản đang có trên máy để đăng nhập lại. Tận dụng tài khoản có sẵn bằng cách đổi mapping Excel (gán nick có sẵn vào ca nuôi, chuyển nick thiếu sang máy khác còn slot trống).
- **CẤM GÁN PASS MAIL VÀO CỘT PASS TIKTOK & TRUY VẾT TỪ BACKUP (2026-09-01)**: Mật khẩu TikTok luôn là chuỗi random gồm chữ hoa, thường, số, ký tự đặc biệt (`d50Xi*Uzk7`), cấm lấy pass mail dạng chữ thường (`qaxvon909063`) điền vào cột pass TikTok. Khi phát hiện sai pass, quét các file backup trong `C:\Users\Kibe\AppData\Local\Taadaa\Tiktok_Reg\workbook-backups\` để lấy lại pass gốc. Chi tiết: `references/account-swap-remapping-and-password-recovery-20260901.md` và `references/tiktok-login-password-recovery-from-backups-and-graph-otp.md`.
- **ĐĂNG NHẬP THIẾT BỊ MỚI VỚI OTP GRAPH API CHO HOTMAIL (2026-09-02)**: Khi TikTok yêu cầu xác minh thiết bị mới gửi OTP về Hotmail, với Hotmail có OAuth2 Token (`gmail_clean_v2.xlsx`), dùng `read_tiktok_otp_from_graph_token` lấy OTP trực tiếp trên PC và nhập vào TikTok qua ADB, CẤM mở app Outlook trên thiết bị để tránh cướp focus/văng phiên. Chi tiết: `references/tiktok-login-password-recovery-from-backups-and-graph-otp.md`.
- **Màn hình Đăng nhập Bottom Sheet (`I18nSignUpActivity`) khi máy chưa có tài khoản**: Khi TikTok ở trạng thái chưa login acc nào, app hiển thị modal trượt "Tiếp tục với email/tên người dùng" đè lên tab Hồ sơ. Khi reconcile/login, kiểm tra `_is_logged_out_auth_screen` hoặc mở trực tiếp luồng login email thay vì cố tìm Account Switcher (tránh timeout tìm switcher anchor).
- **Quy trình Compound Handoff khi xử lý Popup Đăng xuất (Trạng thái tài khoản)**:
  - Khi gặp popup `Trạng thái tài khoản` (*"Tài khoản của bạn đã bị đăng xuất. Hãy thử đăng nhập lại."*), sau khi bấm `OK` đóng popup BẮT BUỘC chạy ngay script `reconcile_tiktok_accounts.py` cho máy đó để kiểm tra inventory tài khoản thực tế trên máy so với `taikhoan_run_safe.xlsx`.
  - Tuyệt đối không dừng lại sau khi chỉ đóng popup; phải xác định rõ nick nào còn/văng và tiến hành login lại (nếu là Hotmail không 2FA thì kiểm tra Outlook app trước khi login TikTok).
  - Chi tiết quy trình & bẫy profile subpage: `references/account-status-logged-out-reconcile-flow-20260901.md`.
- **Bẫy `PROFILE_SUBPAGE_STUCK` do icon 'Số lượt xem hồ sơ' trên Profile Root (TikTok 46.x)**:
  - `_is_profile_subpage` trong `automation_core.tiktok.account_switcher` có thể nhận nhầm Profile root là subpage vì icon mắt trên header có `desc="Số lượt xem hồ sơ"` (`[744,114][816,186]`).
  - Fix chuẩn: Nếu `menu hồ sơ` tồn tại hoặc `_selected_bottom_tab(node_list) is True` (không có prompt lưu tiểu sử), đó là Profile root chính, không phải subpage.
- **Tọa độ mở Account Switcher trên TikTok 46.x Profile Root**:
  - Tên `@username` dưới avatar `(540, 594)` là nút copy, tap `(540, 150)` là bubble status/story ("Trà hay cà phê?"). Để mở bảng trượt Account Switcher ("Chuyển đổi tài khoản"), tap vào display name `(540, 552)` (`id/sv6`).
- **TikTok 46.x Account Switcher Sheet Rendering Latency**: Tên tài khoản trên Profile TikTok 46.x khi tap `(540, 522)` (hoặc sticky header sau scroll) sẽ mở bảng trượt "Chuyển đổi tài khoản" (Bottom Sheet). Cần sleep tối thiểu 1.5s - 2.0s để UI trượt lên hoàn tất trước khi dump XML; tránh gửi keyevent 4 (Back) quá sớm gây lỗi giả `manual-needed:account-switcher-not-open`. Chi tiết: `references/account-switcher-bottom-sheet-latency-20260822.md`.
- **Lock sống từ process khác ĐANG tạo artifact → KHÔNG kill/takeover**: gặp `DEVICE_LOCKED: machine_<N>.lock.json owner_active=True` — kiểm tra PID qua `Get-CimInstance Win32_Process -Filter 'ProcessId=N'`. Nếu process còn sống + `Responding=True` + vừa ghi artifact mới (`ls -t artifacts/ui_dumps/` có file timestamp mới) → process đang chạy flow thật → chờ xong, không kill, không takeover. `owner_active` KHÔNG phải tín hiệu stale (luôn True khi process chết).

- **Preflight force-stop sai khi splash lâu**: uiautomator treo (E=137) làm preflight dump chậm → TikTok splash kéo dài → preflight tưởng treo → `bounded force-stop/relaunch` force-stop TikTok → fail `[01_open] TikTok not foreground after clean launch` về Launcher. Fix: kill atx-agent + restart (`nohup /data/local/tmp/atx-agent server &`) + `POST /uiautomator` TRƯỚC khi chạy runner; verify core capture OK qua `rar.get_ui_xml(serial)` (XML_LEN > 0).

- **Workbook locked by OneDrive/Excel**: `PermissionError [Errno 13]` đọc `taikhoan_dat_v2_updated .xlsx` = file đang mở trong Excel (`Get-Process EXCEL` → MainWindowTitle `taikhoan_dat_v2_updated .xlsx - Excel`). Hỏi user đóng file; KHÔNG kill process Excel tùy tiện (mất dữ liệu chưa lưu). Dùng `openpyxl.load_workbook(..., read_only=True)` hoặc copy temp khi chỉ đọc.

- **TikTok gửi MAGIC LINK, không phải OTP 6 số** (user-confirmed nhiều lần): màn "Kiểm tra hộp thư của bạn / Bạn có thể đăng nhập bằng liên kết" = email đã có TikTok account → login bằng link/password, KHÔNG phải reg mới. Search 6 số là sai hướng; phải mở email TikTok rồi tap nút link ("Xác nhận"/"Confirm"/"Click here"). Gmail path trả `MAGIC_LINK` string khi tap xong; caller xử lý riêng. **Nút đỏ "Xác minh email" trong Gmail app LÀ TAP ĐƯỢC** (HTML link, không phải image) — vấn đề là tọa độ: dùng pixel color scan (TikTok red `r>180,g<120,b<130` → cluster → tap, verified (538,788) máy 34), KHÔNG tin vision coordinate. Flow đầy đủ + resend khi link hết hạn 20 phút: mục "Tap thủ công magic link trong Gmail app" + `references/gmail-magiclink-tap-manual-20260808.md`. **Phân biệt 2 màn cùng có chữ "Kiểm tra hộp thư" (xem mục Bước 07 bên trên):** màn có "Gửi lại email sau N giây" (+ "Đăng nhập bằng mật khẩu") = email CHƯA có TK, TikTok đang chờ xác minh đăng ký qua magic link → `verify_email_pending`, phải GIỮ email đi flow 7c, KHÔNG bỏ qua; màn có "Bạn có thể đăng nhập bằng liên kết" = email ĐÃ có TK → login magic link. Classifier `_classify_after_continue_flat` dùng marker (MAGIC_VERIFY_HINTS vs REAL_OTP_LOGIN_HINTS), priority real-OTP trước. **Sau khi tap link, TikTok hiện lại màn "Kiểm tra hộp thư" KHÔNG có nghĩa fail** — verify có thể đã thành công; mở lại MainActivity check profile mới (banner "Hoàn tất hồ sơ", follower=1, username tự đặt).

- **Gmail auto-sync TẮT là root cause "không có mail"**: `dumpsys content | grep 'auto sync'` → `u0=false` → mail mới không về → search trống → timeout. `settings put global auto_sync 1` KHÔNG ăn trên S7 (vẫn `u0=false`); `cmd sync` không tồn tại trên Android 7; `am broadcast SYNC` cũng không đổi master. Phải bật qua Settings UI (Settings → Tài khoản → Google → account → bật đồng bộ). Khi OTP fail, **ưu tiên check live mail (run_google_live_check) thay vì bật sync tay** — user: "khi OTP k về thì phải chạy flow check mail sống hay k".

- **Khi OTP fail (GMAIL_OTP_TIMEOUT) phải chạy check live Gmail**: gọi `_gmail_account_live_probe` hoặc check siêu tốc qua `checkmail.live` (Chrome CDP port 9222, profile `browser_profile`). **User Rule (2026-09-02):** Nếu Gmail DIE -> báo cáo user & dọn dẹp theo quy trình; Nếu Gmail LIVE -> KHÔNG dừng vô cớ, tiếp tục chạy flow đăng nhập (F5 kéo refresh Gmail trên máy để load OTP). Chi tiết: `references/tiktok-login-gmail-otp-timeout-and-live-check-rule-20260902.md`.

- **"Đăng nhập bằng mật khẩu" trên màn Kiểm tra hộp thư KHÔNG tự nó = email đã có TK** (bài cũ đã đính chính 2026-08-07, xem mục Bước 07): "Đăng nhập bằng mật khẩu" chỉ là link chuyển sang login bằng password trên màn magic-verify — màn "Kiểm tra hộp thư của bạn" + "Gửi lại email sau N giây" + "Đăng nhập bằng mật khẩu" = email CHƯA có TK (`verify_email_pending`), giữ email đi flow 7c. "Đã có TK" chỉ khi màn có marker OTP login thật (`nhap ma`/`gui lai ma`/`resend code`...) hoặc "Bạn có thể đăng nhập bằng liên kết" (login magic link). Workbook có thể SÓT row (email đã reg từ trước nhưng chưa ghi). Phải login (password từ source nếu là pass TikTok, hoặc magic link) rồi ghi workbook với ID thật. **PASS (TikTok) ≠ PASS MAIL** — 2 cột riêng trong workbook; pass mail từ `gmail_clean_v2.xlsx` cột `pass mail` KHÔNG phải pass TikTok, không đoán được pass TikTok từ pass mail.

- **Máy đã login sẵn account → fail `[04_add_account] Không tìm thấy Thêm tài khoản`**: khi máy đang login sẵn account (profile tab hiện `@handle`), flow tìm nút "Thêm tài khoản" trong dropdown nhưng không có (đã có account). Account đang login có thể không nằm trong workbook (reg thủ công/không ghi). Cần đăng xuất trước khi reg mới, hoặc xử lý account hiện tại. Check bằng dump: nếu profile tab hiện `@handle` thay vì màn đăng nhập → máy đang login sẵn.

- **Gmail search-view state loop**: sau khi search, Gmail ẩn `selected_account_disc_gmail` (search overlay) → `_gmail_mailbox_state` trả `target_account_unverified` → loop "mo Gmail inbox" vô hạn. Fix: detect `in_search_view` (`open_search_view_edit_text`/`search_suggestion`/`hub_empty_text`) → bỏ qua check target_selected → reason=ok. Signature: `selected=N inbox=Y reason=target_account_unverified` trong search view = bug đã fix.

- **Empty-state false positive**: "Không có kết quả phù hợp cho TikTok" chứa 'tiktok' → tưởng có kết quả → loop không đổi query. Fix: detect `hub_empty_text` → KHÔNG coi là kết quả → chuyển query tiếp. Và khi hết query → **break**, không `continue` vô hạn.

- **Search query thứ tự**: specific trước, generic cuối: `from:noreply@account.tiktok.com` → `from:noreply@tiktok.com` → `verification` → `code` → `TikTok` (query "TikTok" rộng bắt nhầm search bar/suggestion → candidates=0).

- **`ignore_timestamp` cho Gmail list preview — CẨN THẬN (đã sửa 2026-08-07)**: fast-path2 (`gmail_promo_fast`) từng dùng `ignore_timestamp=True` → khi Promotions có NHIỀU email TikTok (code cũ hôm trước + code mới), nó return candidate ĐẦU TIÊN = code CŨ → `OTP_REJECTED_AFTER_FRESH_RETRY` (run 20260807-124351: lấy code timestamp `'6 Th8'` thay vì code `12:49`). Fix trong `extract_recent_tiktok_otp_from_gmail_list`: mặc định `ignore_timestamp=False` (tôn trọng `_gmail_timestamp_is_after(not_before)`); **fallback lấy `candidates[0]` (trên cùng list = mới nhất) CHỈ khi không candidate nào qua timestamp check** (timestamp tiếng Việt `"6 Th8"` không parse được); **KHÔNG fallback code cũ khi code mới bị `exclude_codes`** (trả None — code cũ là stale, tránh nhập sai). Vẫn tôn trọng `exclude_codes` dù ignore_timestamp.

- **Phải pull-refresh (F5 kéo xuống) Gmail TRƯỚC khi đọc code — KHÔNG đọc preview cũ (user rất tức)**: Gmail không tự sync mail mới ngay khi TikTok gửi; nếu đọc list ngay, chỉ thấy mail cũ (hôm trước) → bấm nhầm mail cũ → code cũ → reject. User: "đã bảo phải vuốt kéo cho mail cập nhật mail ms đã", "cái đụ mẹ đã sửa script là phải refresh gmail = vuốt xuống cho load mail ms r mày vẫn đéo làm r đi bấm vào mail cũ". Fix: chèn `_gmail_pull_refresh(1)` (swipe `540,780 → 540,1500` duration 900 + sleep 7) **NGAY SAU khi vào Promotions, TRƯỚC fast-path `extract_recent_tiktok_otp_from_gmail_list`** (trong `_try_get_otp_gmail_app`, trước đoạn `Fast path 2`). Log signature: `pre-fastpath refresh failed` nếu fail. Verified 5/5 ad-hoc (`hermes-verify-refresh.py`).

- **OTP timeout → live probe RELOGIN → đăng nhập lại Gmail bằng pass source (KHÔNG xóa mail)**: mail vẫn SỐNG nhưng bị **văng khỏi máy** (mất login Gmail) → OTP không về. Flow đúng (user chỉ đạo): OTP không về → check live → nếu màn yêu cầu đăng nhập lại (`GoogleLiveState.RELOGIN`/`"google_relogin"`) → gọi `check_google_account_health_from_gmail(device_id, email, stt=stt)` — hàm này có `submit_password` nhập pass thật (từ `get_email_source_meta(email, stt).get("pass")` — source `gmail_clean_v2`) + `tap_normal_sign_in` → đăng nhập lại để mail nhận OTP. CHỈ xóa mail khi `CAPTCHA`/identity-blocker. Đã patch nhánh catch `AutomationStepTimeout` trong `handle_tiktok_email_otp` (dòng ~8490): `live_status = _gmail_account_live_probe(...)`; `if live_status in (RELOGIN, "google_relogin"): check_google_account_health_from_gmail(...)`; `elif CAPTCHA: xóa`. Verified 9/9 ad-hoc.

- **Anchor account-switcher bị badge thông báo che — tap vào vùng tên/badge vẫn mở dropdown**: TikTok 46.x profile header: tên `@handle` + badge đỏ `9+` cạnh tên CHE mũi tên dropdown → core `find_switcher_anchor` không thấy marker. Tap chính tên user (vd `yobi` bounds `[435,117][645,183]` → tap 540,150) mở được dropdown ("Chuyển đổi tài khoản" + danh sách account + "Thêm tài khoản"). Dùng dump chuẩn (kill atx trước) để lấy bounds chính xác; screenshot để xác nhận. Không tap bừa quanh header (tap 540,250 hoặc 575,230 đẩy về feed).

- **Preflight `open_app()` force-stop nhầm màn login hợp lệ**: preflight thấy TikTok foreground ở `SignUpOrLoginActivity` (màn login sẵn sàng) nhưng vẫn chạy `bounded force-stop/relaunch` → force-stop TikTok → về Launcher → fail `[01_open] TikTok not foreground after clean launch` LẶP LẠI. Fix: nhánh `else` của preflight đọc `dumpsys window windows`, nếu chứa `signuporloginactivity`/`login.v2` → **preserve (return, không force-stop)**. Triệu chứng: log `TikTok already foreground; bounded force-stop/relaunch recovery` rồi `[01_open]` fail ngay sau đó.

- **Đừng kết luận "hardware limit" quá sớm**: nhiều run fail `OTP screen unavailable` tưởng S7 kill activity khi chuyển app. User bác bỏ: "mấy máy khác chạy được mắc gì đống máy này lỗi". Root cause thật: (a) email không tới do auto-sync tắt, (b) TikTok gửi magic link không phải OTP 6 số, (c) email đã reg trước (login chứ không reg), (d) máy login sẵn account. Kiểm tra mail arrival + sync state + account state TRƯỚC khi quy kết phần cứng.

- **Workbook locked by OneDrive**: Use `openpyxl.load_workbook(..., read_only=True)` or copy to temp first

- **UI XML dump hangs**: UIAutomator can fail on some Samsung devices → use manual ADB

- **Google AssistedSignInActivity**: Always appears on fresh install → dismiss with back

- **Google Play post-install popups** (2026-07-29): On devices where Play Store hasn't been initialized, `force-stop` + `monkey` can trigger Play ToS or PlayCore ("Tải xuống qua Play"). Dismiss by tapping "Chấp nhận" then "Tải xuống qua Play", then re-issue monkey. Handled in `_start_tiktok_and_wait()` via `_dismiss_play_popups()`.

- **2FA required**: New TikTok accounts often require 2FA → read secret from workbook 2FA column

- **Post-login popups**: Contact permission + security check → dismiss both

- **Account switcher navigation fails**: Occurs when device has no accounts logged in (reconcile script expects existing accounts)

- **API mismatch**: `automation-core` may change. Check `pip show automation-core` version. Consumer imports must match installed version (e.g., `soft_reboot_and_wait` → `reboot_and_restore` in 0.2.40)

- **AdbKeyboard broadcast timeout on some devices**: On SM-G930W8, `am broadcast ADB_KEYBOARD_INPUT_TEXT` hangs subprocess (result=-1, never exits). Text still enters correctly — use fire-and-forget with short timeout or `input text <base64>` via shell. Verify with UI dump after.

- **Consent popup after data clear**: Full-screen "Đồng ý và tiếp tục" dismissed by swipe up, NOT tap. Handle in both adapter and inventory startup wait.

- **Profile navigation fallback — coordinate phải là `(972, 1883)`, KHÔNG `(972, 1857)` (sửa commit `0a491bd`, máy 34 live-proven)**: bottom tab "Hồ sơ" bounds thật `[864,1864][1080,1903]` → center **`(972, 1883)`**. `(972, 1857)` cao hơn **26px trên tab** → tap trượt → máy nằm lại feed dù `is_profile_tab_selected()` log "profile selected" (node selected dương tính giả trong feed) → `SWITCHER_ANCHOR_AMBIGUOUS` loop vô hạn. Sửa cả `COORD["profile_tab"]` + bottom-right fallback + `_profile_tab_node` (clamp `cy<1870 → 1883`). Bài học: **hardcode tọa độ tab lệch vài px giữa các máy/dump** — khi tap không vào profile, dump bounds tab để lấy center thật, đừng tin coordinate hardcode cũ hoặc node dump (node có thể trả 1857 dù màn thật 1883).

- **automation-core `build_machine_launch_plan` signature drift**: 0.4.19 rejects `max_workers`; 0.4.20+ *requires* it (and `requirements-automation-core.txt` may pin newer than the installed wheel — always verify with `pip show automation-core` / `inspect.signature` before dispatching a batch). Both `scripts/run_social_batch_deferred.py` and `_run_all_targets.py` shim it: `_LAUNCH_PLAN_PARAMS = inspect.signature(build_machine_launch_plan).parameters` then pass `max_workers` only `if "max_workers" in _LAUNCH_PLAN_PARAMS`. Keep this consumer-side pattern — never edit automation-core.

- **Never foreground-sleep-poll a running batch**: interrupting a foreground command (e.g. Ctrl-C on `sleep 90 && tail`) kills the whole background process tree (orchestrator + workers) in the same Hermes session. Use `process(action='wait')` (clamps to ~180s, repeat) or rely on `notify_on_complete`. Detached workers may keep running after the parent dies and leave `owner_active=True` locks whose PID is already dead — always verify by PID liveness, not by `owner_active`.



## Device Lock Convention



- Lock dir: `C:\Users\Kibe\.codex\device-locks\`

- Files: `machine_<N>.lock.json` and `serial_<SERIAL>.lock.json`

- Remove stale locks where PID is dead before starting

- Acquire lock before touching device, release in finally

- **A crashed batch leaks reserved locks**: if the orchestrator dies after `acquire_device_lock` but before `lease.finish()`, every reserved target keeps `machine_<N>.lock.json` + `serial_<SERIAL>.lock.json` with the same dead PID. The next batch then reports every target `SKIPPED_DEVICE_LOCKED`. Cleanup rule: remove a lock only when its `pid` is dead (verify via `tasklist /FI "PID eq <pid>"`) AND its `project` is `Tiktok_Reg` — never touch `tiktok-upload` or other projects' locks. Note `owner_active` stays `True` after parent death, so it is NOT a reliable staleness signal; PID liveness is. Re-runnable cleanup: `scripts/clean_stale_device_locks.py`.





## Registered-vs-unregistered routing (bắt buộc)



Không được kết luận email đã có TikTok chỉ từ marker chung `Xác minh email`, `Nhập mã`, `Gửi lại mã`, hoặc mail TikTok verification. Phải ghi nhận **entry surface trước submit** (login identifier vs signup/create-account), submit một lần, rồi recapture TikTok UI mới để phân loại: login surface + password/login OTP/login-link → existing-account login; signup surface + `Xác minh email của bạn`/`hoàn tất đăng ký`/signup magic-link/signup OTP → new registration; thiếu hoặc xung đột evidence → `UNKNOWN` fail-closed. `PASS MAIL` không thay cho TikTok PASS; registered nhưng thiếu ID/PASS → `REGISTERED_CREDENTIALS_MISSING`, không chạy reg đè. Chi tiết matrix và negative cases: `references/registered-vs-unregistered-routing.md`.



## RULE 3 BƯỚC FIX MỌI LỖI (2026-08-10, phủ all repo + core)



BẤT KỲ lỗi nào (UI dump/capture-invalid/popup/terminal, kể cả không phải UI) → TỰ chạy 3 bước fix NGAY, KHÔNG chờ user nhắc: B1 ATX-kill (chạy khi gặp lỗi bất kỳ) + B2 force-stop + B3 soft reboot (B2/B3 mỗi 1 lần/turn/máy) → lỗi lặp lại chỉ ATX-kill + coordinate fallback có evidence → fail MANUAL_REVIEW. Nguồn: PROJECT_RULES.md các repo Taadaa + automation-core/docs/ui-compatibility-contract.md (commit 2026-08-10).

