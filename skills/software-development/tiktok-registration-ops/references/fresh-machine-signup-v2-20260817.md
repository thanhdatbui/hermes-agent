# Fresh-machine TikTok signup (I18nSignUp / signup v2) — live 2026-08-17, máy 76

Máy MỚI TINH (chưa từng login TikTok) reg hotmail: flow `social_reg_v1.py` cũ
(profile tab → add account) fail `[02_profile]`. Đã patch bypass vào main flow;
file này ghi lại map tọa độ + hành vi LIVE để tái dựng/debug.

## Trình tự màn hình thực tế (máy 76, serial 9885b64d56305a3731)

1. **I18nSignUpActivity** (mở app lần đầu, chưa có acc): nền "Hồ sơ" mờ + login
   bottom-sheet. Mặc định tab SĐT: field `VN +84 | Số điện thoại`, nút đen
   "Đăng nhập", "hoặc", nút trắng viền xám:
   - "Tiếp tục với email/tên người dùng" — bounds **[72,1157][1008,1313]**, clickable,
     center **(540,1235)**. ⚠️ Đoán y≈640 từ ảnh vision là SAI (miss).
   - "Tiếp tục với Facebook" [72,1349][1008,1497].
   - Link "Tạo tài khoản" (dưới cùng), footer Điều khoản.
2. Tap email → màn **"Email hoặc TikTok ID"** (vẫn I18nSignUpActivity):
   - EditText **[138,656][852,716]** (class chuẩn android.widget.EditText, placeholder
     "Email hoặc TikTok ID").
   - Nút "Đăng nhập" bounds **[414,848][666,908]**, center **(540,878)**.
   - Phía dưới: icon phone, "..." , nút "Tạo tài khoản" [571,1668][845,1719].
3. Tap Đăng nhập (email đã điền) → **SignUpOrLoginActivity** = màn **"Nhập mã" (OTP)**:
   - Tiêu đề "Nhập mã"; text "Sử dụng liên kết này hoặc nhập mã được gửi đến
     `<email>`"; **6 ô mã 6 chữ số**; "Gửi lại mã 57s" (đếm ngược); checkbox
     "Ghi nhớ thông tin đăng nhập" (tích sẵn); link xanh **"Đăng nhập bằng mật khẩu"**
     (đổi sang nhập password, không cần OTP).
   - Nhánh này = cùng chỗ `handle_tiktok_email_otp` — sau khi qua đây là DOB →
     password như flow cũ. User: "chỉ khác đoạn đầu thôi còn đoạn sau như nhau".

## ⚠️ Bypass [02_profile] FAIL live — detect fresh-signup KHÔNG dựa vào "không có profile" (2026-08-17 chiều)

Patch `_is_fresh_signup` (thêm vào main flow bước [2]) KHÔNG kích hoạt trên máy thật: màn
I18nSignUpActivity vẫn chứa node `desc='Hồ sơ'` (tab Profile) trong accessibility tree →
`_is_profile_screen_xml(xml_b2)` trả True → điều kiện `... and not _is_profile_screen_xml(xml_b2)` False
→ vẫn rơi vào `go_to_profile` → `[02_profile]` fail y như cũ.

**Bài học:** detect màn fresh signup PHẢI dựa vào **Activity** (`I18nSignUpActivity` /
`com.ss.android.ugc.aweme.account.login.auth.*`) hoặc marker đăng ký rõ ràng
(`tao tai khoan`, `tiep tuc voi email`/`tiếp tục với email/tên người dùng`) — KHÔNG bao giờ
dựa vào "không có node profile tab" vì tree của màn signup vẫn expose tab Profile.

## Trình tự màn hình sau I18nSignUp — flow reg v2 hoàn chỉnh (live máy 76, 2026-08-17)

Máy 76 (serial 9885b64d56305a3731) đã đi THÀNH CÔNG tới màn Tạo mật khẩu (đây là lần đầu token-OTP
chạy end-to-end tới đây):

1. I18nSignUp login sheet → tap "Tiếp tục với email/tên người dùng" **bounds [72,1157][1008,1313] center (540,1235)**
   (đoán y≈640 từ vision SAI).
2. Màn "Email hoặc TikTok ID" — EditText [138,656][852,716], nút "Đăng nhập" (540,878).
3. Tap Đăng nhập → **SignUpOrLoginActivity** = màn "Nhập mã" OTP 6 ô (link xanh "Đăng nhập bằng mật khẩu").
4. **Đọc OTP qua token Graph API CHẠY LIVE**: `read_tiktok_otp_from_graph_token('9885b64d56305a3731',
   'LilyanLederhos64090@hotmail.com', timeout=60)` → `'585970'` — KHÔNG mở Outlook app. Nhập vào 6 ô
   (tap ô đầu + `ADB_KEYBOARD_SET_TEXT` base64 cả 6 số) → TikTok xác nhận → chuyển DOB.
5. Màn **"Ngày sinh của bạn là ngày nào?"** — `fill_birthday(device, '', stt=76)` fallback picker
   → `'1 tháng 1, 1999'` → tap Tiếp tục (540,1728) → **màn "Tạo mật khẩu"**.
6. Màn **"Tạo mật khẩu" (Create password — dành cho acc MỚI)**: yêu cầu 8-20 ký tự + 1 chữ + 1 số +
   1 ký tự đặc biệt; nút **"Bỏ qua" (Skip)** góc trên phải; nút "Tiếp tục" disabled tới khi pass hợp lệ.
   ⚠️ `fill_password_and_login` CŨ chỉ nhập pass CÓ SẴN (từ ACCOUNTS) — KHÔNG xử lý màn create-password.
   Quyết định "Bỏ qua" vs "tạo pass mới" treo chờ user (chưa chốt).

## DOB fallback PHẢI RANDOM (user correction 2026-08-17)

User bác giá trị cứng `01/01/1999` trong `fill_birthday` ("cái này đâu ra v mặc định fallback về ngày này à,
t nghĩ tạo ngẫu nhiên đi nhé, h lỡ r nhưng lượt sau sửa lại"). Lượt SAU: sửa `fill_birthday` fallback thành
sinh ngẫu nhiên hợp lệ — 18+ tuổi, tháng/ngày hợp lệ — KHÔNG dùng mốc cố định. "Lỡ r" = acc đã tạo bằng
01/01/1999 chấp nhận, chỉ đổi lượt sau.

## Dynamic email-icon detection — ưu tiên icon VUÔNG nhỏ, không phải nút dài (fix `2718a1e`, live máy 75)

`choose_email_login` fallback dynamic detection ("các node clickable ≥60px dưới EditText, chọn leftmost
theo (y,x)") CHỌN NHẦM **nút pill "Đăng nhập"** (bounds [72,872][1008,1028] w=936 h=156) thay vì icon
email vuông 144×144 → tap trúng nút Đăng nhập → màn SĐT + dòng đỏ "⚠️ Nhập số điện thoại hợp lệ" →
script tưởng "không có email mới" → STOPPED sai `[07] Tat ca N email cua STT da co TK TikTok`.

**Fix:** candidate phải kèm `squareness = abs(w - h)`; ưu tiên pool chỉ gồm candidate gần-vuông
(`squareness < 40`, icon email ≈144×144), rồi mới min theo (y,x). Verify live: chọn đúng (241,1693)
thay vì (540,950). **Cùng class:** mọi "icon/button chọn leftmost clickable" phải ưu tiên hình dạng
vuông/phù hợp, đừng lấy cái to nhất bên trái.

## Patch script khi process ĐANG CHẠY = vô hiệu (phải KILL + restart)

Python load source lúc process START — patch file giữa run KHÔNG có hiệu lực. Triệu chứng lừa (máy 75
v2→v4): `grep` file thấy marker mới, test import thấy marker, NHƯNG log vẫn nhánh cũ (`[2] Go to profile
tab` dù đã thêm bypass) → vì process start TRƯỚC patch. Trước MỌI rerun sau sửa code:
`wmic process where "Name='python.exe'" get ProcessId,CommandLine | grep "social_reg_v1.py <stt>"` →
`taskkill /T /F <pid>` → verify không còn process → chạy lại. (Cùng trap đã ghi cho qualify/download
loop ở taadaa-farm-ops-rules §8.)

## Gõ email vào field — 3 pitfall đo (live)

- **AdbKeyboard `ADB_KEYBOARD_SET_TEXT` broadcast THAY THẾ toàn bộ nội dung field**
  (không append ở cursor). Gõ phần thiếu vào field đã có chữ → ghi đè mất phần cũ.
- **`am broadcast -a ADB_CLEAR_TEXT` KHÔNG clear** (trả result=0 nhưng field giữ
  nguyên). Xóa bằng: tap field (đặt cursor cuối) + lặp `input keyevent 67`, hoặc
  dùng `type_into_node(..., clear=True)` của script.
- **Vision OCR đọc SAI EditText bị scroll**: field thật `LilyanLederhos64090@hotmail.com`
  nhưng vision thấy `Lederhos64090@hotmail.com` (phần đầu tràn khỏi khung). Luôn
  verify giá trị bằng **UI dump** (`EditText text='...'` attribute), không tin OCR.

## Bypass [02_profile] khi màn fresh signup — FINAL FIX (live máy 75, 2026-08-17, commit fc4db19)

Detect bằng marker CỤ THỂ (`i18nsignup` / `tao tai khoan` / `tiep tuc voi email` /
`so dien thoai`+`dang nhap`...) VẪN FAIL trên máy thật: màn I18nSignUpActivity chứa
node `desc='Hồ sơ'` (tab Profile) trong accessibility tree nhưng các marker LẠI có
trong dump — tuy nhiên có lần XML b2 chưa load đủ (splash/loading) nên marker miss.
**FINAL (đơn giản + đúng): `_is_fresh_signup = not _is_profile_screen_xml(xml_b2)`**
— MỌI màn không phải profile screen thật (login/signup/consent/onboarding/home-feed)
đều bypass `go_to_profile`, nhảy thẳng `choose_email_login`. Chỉ màn profile thật
(≥2 profile markers: `da follow`/`follower`/`thich`/`sua ho so`...) mới đi nhánh
add-account cũ. Verify live máy 75: log `[2] Màn signup mới → bypass profile`.

## Màn home feed (anonymous) — choose_email_login phải tap Profile tab mở login sheet (live máy 75)

Máy mới tinh mở TikTok lần đầu có thể RƠI VÀO HOME FEED anonymous (`Cộng đồng`/
`Bạn bè`/`Trang chủ`/`Hồ sơ`) — KHÔNG có login sheet. `choose_email_login` hiện có
nhánh đầu: detect home markers (không có `dang nhap`/`tiep tuc voi email`/... và
≥2 home markers) → tap tab Hồ sơ (`_profile_tab_node` hoặc fallback (972,1857)) →
đợi bottom-sheet login render → mới vào `wait_for_text(["Đăng nhập"...])`.

## First-launch onboarding — "Vuốt lên để xem thêm" (live máy 75, 2026-08-17)

Máy CÀI MỚI TikTok lần đầu có màn onboarding "Vuốt lên để xem thêm" (swipe up
gesture) + App Open Ad (không có nút skip → script swipe up — `[open-ad] no skip
button -> swipe up`). Đây là màn KHÔNG có profile tab → bypass logic xử lý đúng
(`not _is_profile_screen_xml` trả True). User hướng dẫn: "kiểm tra bấm vào profile
đc k, k đc thì vuốt cái cho nó qua" — swipe up để qua onboarding.

## TẠO MẬT KHẨU — KHÔNG bao giờ chọn "Bỏ qua" (user directive 2026-08-17, ĐÃ CHỐT)

Màn "Tạo mật khẩu" (acc MỚI, signup v2): user CHỐT là **PHẢI tạo password** để ghi
vào excel — "phải tạo mật khẩu để ghi excel chứ, m bỏ qua r phải tốn công chạy
script đổi mật khẩu lần nữa à". KHÔNG tap "Bỏ qua"/Skip. `fill_password_and_login`
nhận `tiktok_pw` sinh bằng `make_tiktok_password()` — **random thuần** (user: "k
sinh password từ mail pass mà phải sinh random"): letter upper+lower + digit +
special, 10-16 ký tự shuffle, KHÔNG derive từ email pass, KHÔNG dùng pattern `@Ks`
(code đã đúng, chỉ bỏ param thừa). Sau create-password → post-auth screens → SUCCESS.

## Display name — rút gọn + chế tiếng Việt (user rule 2026-08-17, commit 361ff76)

User bác tên dài (`LilyanLederhos64090`): "gì đặt tên dài thế, t ns lấy mấy từ đầu
thôi... tốt nhất là lấy mấy từ đó xong chế thành tiếng việt, kiểu lyan thì đặt là
liên hoặc linh gì đó". `make_tiktok_name(email)`:
1. prefix = chữ cái đầu (cắt tại chữ số), cắt tại chữ hoa thứ 2 nếu ≥3, giới hạn 8 ký tự.
2. Tra `_VI_NAME_MAP` (prefix → tên Việt gần âm, probe 3-6 ký tự): Lilyan→Linh,
   Gaye→Gia, Debi→Diệp, Rudy→Rudy, Ruffus→Rô, Ancil→An, Steveneudora→Thịnh,
   Florencenaomi→Phương...
3. Không có map → giữ prefix (hoa chữ đầu); quá ngắn → fallback random `_VI_NAME_FALLBACK`.
Test: 8 email thật → tên gọn tiếng Việt. Rule: KHÔNG dùng cả username dài.

## ACCOUNTS hardcode — bắt buộc thêm STT mới

`social_reg_v1.py` tra `ACCOUNTS` (list dict stt→device) chứ KHÔNG đọc workbook
cho việc resolve device. Detector `_detect_clean.py` ra target (kể cả STT 75-80)
nhưng script `Không có STT 75` exit 1 nếu thiếu entry. Thêm máy → thêm
`{"stt": N, "device": "<serial>", "email": "", "pass": ""}` vào list.
Grep check: `grep -n '"stt": *75' social_reg_v1.py`.

## ⚠️ OTP field `enabled="false"` — root cause kẹt OTP mãi (live máy 75, chiều 2026-08-17)

Màn "Nhập mã" (OTP, SignUpOrLoginActivity) trên máy 75 có **1 EditText WIDE**
`[96,660][984,816]` nhưng **`enabled="false"`** (dù `focused=true` `focusable=true`).
Hệ quả chuỗi lỗi:
1. `list_edittext_nodes` filter `attrs.get("enabled") == "false"` → SKIP node → `nodes=[]`.
2. `enter_otp_code` rơi vào fallback `tap(540,900)` — nhưng field ở y≈738, nên
   tap (540,900) trúng vùng **"Gửi lại mã"** → OTP không vào field → submit Enter
   vô nghĩa → màn "Xác minh email" lặp → `timeout login success` → PENDING exit 2.
3. Triệu chứng lọc (resume lặp 4-5 lần): log `[otp-enter] Không có EditText, tap
   center (540, 900)` + `field vẫn text cũ` (OTP cũ 573199 còn nguyên) + vòng
   `[8b-N] Xác minh email → fetch → enter` vô hạn.

**Cách ĐÃ verify hoạt động (máy 76, `'585970'` vào 6 ô ok):** `ADB_KEYBOARD_SET_TEXT`
broadcast base64 — set-text **không bị chặn bởi `enabled=false`** vì nó ghi qua
IME/focused field, không phải keyevent. ⚠️ Keyevent (`input keyevent 67` xóa,
`input_text`/AdbKeyboard key-event) BỊ CHẶN trên field disabled — DEL không xóa,
gõ không vào (đã verify máy 75: 30×DEL + input_text không đổi field).

**✅ FIX CUỐI CÙNG (user hướng dẫn, commit `0ed1c4c`, CHẠY THẬT QUA ĐƯỢC OTP máy 75):**
bấm **Back 1 cái** (`keyevent 4`) → field mở khóa + xóa sạch code cũ → `get_ui_xml`
lại → `list_edittext_nodes` giờ THẤY EditText → `type_into_node(code, clear=True)`.
Live log: `Không thấy EditText → bấm Back xóa code cũ → Sau Back: thấy EditText
(495, 600) → gõ code mới` → qua OTP → `[8] Fill password` → `[8b] post-auth`.
Lưu ý: 4 commit OTP trước (tap-bounds/input_text/set-text/resend) bị user yêu cầu
**revert cả** vì 0/4 có proof (xem mục revert dưới) — chỉ Back-fix này giữ lại và
có proof. Nếu sau Back vẫn không thấy EditText → `fail_otp_no_edittext_after_back`
+ ảnh + dừng chờ user.

## OTP code cũ/hết hạn trong inbox — PHẢI bấm "Gửi lại mã" trước khi fetch (user hướng dẫn 2026-08-17)

User: "75 bị treo r chắc otp lỗi, gặp này bấm resend lấy OTP mới nhập lại".
`_fetch_post_auth_email_code` đọc code MỚI NHẤT trong inbox — nhưng nếu TikTok
chưa resend thì "mới nhất" vẫn là code CŨ (hết hạn/sai) → nhập mãi fail → vòng
lặp vô hạn. Nhánh màn "Xác minh email"/"nhập mã" còn sót phải: **tap "Gửi lại mã"
→ sleep ~6s (chờ mail mới) → fetch → enter**. Resend trước MỖI lần fetch, không
chỉ khi fetch fail. (Đã code trong commit `9bb6ae2` — sau đó bị revert theo lệnh
user, xem dưới.)

## Bài học revert — fix chưa có proof KHÔNG được giữ (user quyết 2026-08-17)

4 commit fix OTP (`b35432a` tap-bounds, `b984881` input_text, `a2ef63c` set-text,
`9bb6ae2` resend) bị user yêu cầu **revert CẢ 4** vì **0/4 có proof**: máy 75 vẫn
kẹt OTP, chưa reg xong — commit ghi "verify" chỉ là lý thuyết, không phải máy
SUCCESS. Kết luận: **mỗi fix phải có bằng chứng chạy thật (máy qua được đúng bước)
mới commit giữ; mò mẫm nhiều vòng + tự chạy lại nhiều lần = vi phạm**
(NO-MANUAL-TAP / user-guide-driven, skill `taadaa-farm-ops-rules` §3-4). Revert
riêng: `git revert --no-commit <các sha>` theo thứ tự ngược → verify enter_otp_code
về code gốc → commit revert CHỈ file đó (không cuốn AGENTS.md/project_paths.py
dirty sẵn).

## MACHINE_IN_USE gate — process cũ còn sống chặn re-run (live máy 75, 2026-08-17)

Chạy lại script mà process cũ chưa thoát → `[gate] MACHINE_IN_USE` STOPPED ngay.
Process ẩn: wmic chỉ thấy cặp venv-core024 + uv-python (2 PID cùng cmdline) khi
process sống qua background-session. `taskkill /F /PID <chính xác>` (không dùng
`//F` — git-bash mangle). Verify sạch: `wmic ... | grep social_reg` rỗng trước
khi chạy lại. Liên quan pitfall "patch giữa run vô hiệu" — kill + restart sau
mỗi sửa code, và kill HẾT process cũ trước mỗi rerun.

## Vòng [8b] kẹt ở màn "Tạo tài khoản" — script nhầm EMAIL-FIELD thành OTP → FIX ĐÃ IMPLEMENT (commit `4bd325c`, live máy 75)

Sau khi qua OTP (Back-fix), vòng `[8b]` lặp "Xác minh email → fetch → enter_otp_code"
vô hạn; kill giữa chừng thấy máy đứng ở màn **"Tạo tài khoản"** (signup v2, màn
NHẬP EMAIL: field chứa `623132` = OTP bị gõ nhầm vào EMail field, link "Chuyển
sang dùng số điện thoại", nút "Tiếp tục"). Màn này KHÔNG phải OTP: cần nhập email
full + Tiếp tục, không gõ code. Phân biệt: màn email có "Chuyển sang dùng số
điện thoại" + nút đen "Tiếp tục" + field WIDE; màn OTP có "Gửi lại mã"/đếm ngược
+ checkbox "Ghi nhớ thông tin đăng nhập" (bounds field OTP [96,660][984,816]).

**FIX (đã implement + chạy thật qua bước này):** trong `handle_post_auth_screens`,
thêm nhánh TRƯỚC nhánh "Xác minh email":
```python
if ("dia chi email" in flat and "chuyen sang dung so dien thoai" in flat) or (
        "tao tai khoan" in flat and "dia chi email" in flat and "tiep tuc" in flat):
    # type email full + tap Tiếp tục → TikTok gửi OTP MỚI
```
Live log proof (resume10): `[8b-0] Tạo tài khoản email form → type full email +
Tiếp tục` → `signup email form: found 1 EditText` → chuyển được sang màn OTP
(`[otp-enter] Thử node đầu tiên: (540, 738)`). ⚠️ Khi patch block này lưu ý giữ
indent 8 spaces (patch tự động dễ đẩy thành 16 → `IndentationError`).

## ⚠️ "Email mất ký tự đầu" = 90% là OCR/scroll ảo, KHÔNG phải type lỗi — luôn verify bằng UI dump (live máy 75, CUỐI session, user chốt)

Dù nhánh 4bd325c chạy (tìm EditText + type + tap Tiếp tục), vòng [8b] vẫn lặp màn
"Xác minh email". Vision đọc field thấy **`yeGaebel4667@hotmail.com` → tưởng mất
`Ga`** → kết luận "type rớt prefix → script gõ OTP nhầm". User BÁC: "có sai lồn
đâu, do cái hiển thị của nó k đủ kí tự, t kéo con trỏ về bên trái vẫn đúng
hotmail mà" — **XML dump xác nhận `EditText text='GayeGaebel4667@hotmail.com'`
ĐẦY ĐỦ và ĐÚNG** (bounds [162,570][828,630]).

**Bài học chốt (CÙNG CLASS pitfall Lilyan sáng máy 76):** vision/OCR trên EditText
bị scroll tràn khung LUÔN báo sai thiếu prefix. TRƯỚC khi kết luận "gõ lỗi" →
`get_ui_xml` + đọc `EditText text=` attribute (nguồn sự thật duy nhất). Chỉ khi
UI dump thực sự thiếu ký tự mới tính chuyện retype. Quy tắc type email/password
màn signup:
1. Sau `type_into_node(...)` LUÔN `get_ui_xml` lại → so sánh `EditText text=`
   với chuỗi mong đợi (STRICT, không tin vision).
2. Thiếu THẬT (UI dump xác nhận) → tap field, focus / clear=True + type lại, verify.
3. Nút "Tiếp tục" xám = field chưa hợp lệ — đừng tap mù, nhưng xám cũng có thể do
   TikTok chưa kích hoạt, đừng vội suy diễn email sai.

## Màn "Kiểm tra hộp thư của bạn" (magic-link) — XUẤT HIỆN SAU khi tap "Tiếp tục", khác hẳn màn nhập email (live máy 75, cuối session)

Sau khi nhánh 4bd325c gõ email + tap "Tiếp tục" → TikTok hiện **màn \"Kiểm tra
hộp thư của bạn\"** (magic-link): tiêu đề đó + \"Bạn có thể đăng ký bằng liên kết
được gửi đến <email>\" + nút duy nhất **\"Gửi lại email\"** — KHÔNG có field nhập
mã. User cảnh báo phân biệt rõ: màn nhập email (có field + \"Chuyển sang dùng số
điện thoại\" + nút \"Tiếp tục\") ≠ màn magic-link (chỉ có nút \"Gửi lại email\").
`[login-success]` log sai khi nhận `hint='Kiểm tra hộp thư của bạn'` làm success
→ rồi `[10] Ensure profile` → `[02_profile]` STOPPED vì chưa thực sự vào app.

**Xử lý đúng:** màn này phải qua `read_tiktok_magic_link_from_outlook_app` (tap
link trong Outlook app / đọc magic-link mới từ inbox). ⚠️ Fix TypeError cần thiết
(commit `26ee634`): chỗ gọi trong `handle_tiktok_email_otp` truyền `password=`
kwarg — hàm KHÔNG nhận password → `TypeError: got an unexpected keyword argument
'password'` → script fail ngay trước khi vào magic-link nhánh. Bỏ `password=`
khỏi lời gọi. (Trạng thái: Back-fix + email-form fix có proof; bước magic-link
chưa verify xong — chờ user hướng dẫn hướng xử lý link.)