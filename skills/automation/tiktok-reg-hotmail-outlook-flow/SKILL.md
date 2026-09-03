---

name: tiktok-reg-hotmail-outlook-flow

description: Đăng ký TikTok bằng hotmail qua Outlook app — 4 máy 38/54/57/66, login Outlook trước rồi reg. Bao gồm mọi fix 2026-08-16 (quick-note variant B, icon email bounds, OTP dính DOB).

---



# TikTok Reg với hotmail qua Outlook app


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
- Phân tầng trước khi dừng: lỗi cơ học/UI đã có handler (OTP hết hạn, nút gửi lại mã, popup bàn phím, DOB/picker chậm, timeout login-success do nghẽn, dropdown/add-account) phải tự xử lý theo handler, recapture và retry có giới hạn.
- Chỉ dừng gọi user khi gặp màn hình lạ/chưa có handler, captcha/block bất thường, proxy/ADB không thể phục hồi, hoặc nghi ngờ dữ liệu/mapping sai. Khi dừng: giữ lock + giữ nguyên màn hình + chụp ảnh thật + báo blocker.
- **Actionable Farm Alert khi Fail/Pending:** Nhánh `not ok` trong `_do_register` (`social_reg_v1.py`) tự động gọi `send_farm_machine_alert` bắn ảnh có gắn banner đỏ `[MAY <N>]` và đầy đủ 4 bước thực thi (lệnh inspect, flow file, log file, canary cmd) về kênh Farm Alerts.
- Không retry mù: xác định đúng STT/email/run artifact trước; mỗi nhóm lỗi tối đa 2 meaningful attempts.
- Mọi thao tác OTP phải xác minh field hiện tại là OTP (label/shape/package TikTok), tuyệt đối không nhập OTP vào password field. Nếu field không xác định được, dừng nhóm đó và lưu artifact.
- Mọi lock phải dùng đúng root lock mà runner/cron dùng, tạo atomic và preflight cả queued/running; không tự tạo lock ở runtime/archive khác để giả bảo vệ.
- Ảnh gửi user phải là ảnh thật `MEDIA:<path>` trên dòng riêng, đã đọc/đối chiếu trước khi báo cáo.

## Trigger

- User yêu cầu reg TikTok cho máy hotmail (38/54/57/66 trong `D:\Taadaa\Tiktok_Reg`)

- Hotmail đã login vào Outlook app (hoặc cần login trước)



## Flow chuẩn

1. **Login hotmail vào Outlook app TRƯỚC** (repo `D:\Taadaa\Hotmail`, runner `flows/login_outlook_one_machine.py`):
   - Tuần tự TỪNG MÁY (OTP recovery dùng chung `thanhdatbui1995@gmail.com`)
   - Env: `OTP_MAIL_USER`/`OTP_MAIL_APP_PASSWORD` (Gmail app password, IMAP), `OTP_SENDER_HINT="microsoft"` (bắt buộc — default "google" lọc mất mail Microsoft)
   - Pass lấy từ `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`

2. **Verify login**: mở Outlook → tap avatar (chữ A) góc trái → **dòng đầu drawer = target email** = active mailbox (user-taught 2026-08-16) → đóng drawer

3. **Chạy reg chuẩn (BẮT BUỘC ĐI TỪ LOGIN, CẤM ĐI TRỰC TIẾP FORM ĐĂNG KÝ)**: `python social_reg_v1.py <stt> --email <mail> --ss`
   - **Quy tắc workflow bắt buộc (user 2026-08-18)**: Mở TikTok → Tab Hồ sơ → Chọn "Đăng nhập" → Chọn tab "Email / Tên người dùng" → Nhập email → TikTok phát hiện email chưa có tài khoản → Bật popup "Tạo tài khoản mới" → Tap "Tạo tài khoản mới" → Đi tiếp sang OTP/DOB.
   - **CẤM TUYỆT ĐỐI**: Tự bấm vào link "Tạo tài khoản" ở chân popup login hoặc đi vào form signup_entry trực tiếp (gây lệch state machine và kẹt checkbox lưu thông tin đăng nhập).
   - Đã có account TikTok cũ → `--full-scope-takeover` ở `_run_all_targets.py`
   - Màn giữa chừng (password/DOB) → `--resume` (KHÔNG chạy lại từ đầu)



## Pitfalls đã fix (2026-08-16)

- **Quick-note variant B**: popup privacy 3 mục ("Những nội dung quan trọng...", "Quyền riêng tư...", "Bạn đang nắm quyền kiểm soát") KHÔNG có title "Ghi chú nhanh" — detect 2/3 marker + swipe + tap OK (540,1705); nút OK WebView opaque không nhận tap trừ khi swipe trước

- **Icon email layout mới**: hàng icon đăng nhập nhanh ở y 800-1100 (KHÔNG phải 1540-1800 cũ), icon trái nhất = email, tap theo bounds + fallback detect động (clickable view vuông dưới EditText SĐT, chọn trái nhất)

- **OTP dính field DOB**: sau submit OTP TikTok chuyển màn DOB → digits vào field sinh nhật → `enter_otp_code` detect DOB + clear_field sau submit; nếu lỡ dính → chạy `fill_birthday(device, dob, stt)` rồi `--resume`

- **Password field race**: WebView render chậm → `_outlook_app_password_node_with_retry` (re-dump 5 lần)

- **Auto-rotate**: cấm bật xoay màn (user căm thù) — mỗi lần mở app set `accelerometer_rotation 0` + `user_rotation 0` + `wm user-rotation lock 0`; máy 54/57/66 từng tự bật lại → luôn re-lock trước khi chạy

- **ADB mất máy**: `wm user-rotation lock` làm restart adb daemon → máy rớt khỏi `adb devices` vài giây → chờ reconnect, đừng hoảng



## Verify thật

- Artifact JSON `drawer_top_line` = email active trong drawer (bằng chứng login)

- Workbook tracking: `taikhoan_dat_v2_updated .xlsx` có row (Tik=STT-1) + backup file trước write

- Ảnh `screenshots_social/<stt>_09_result_*.png` = màn thành công/đang chờ

- **Verify account vừa reg có trên máy bằng account switcher** (user yêu cầu, 2026-08-16 máy 57): build MiniAdapter (`dump_ui`=get_ui_xml, `tap`, `back`, `tap_profile`=(972,1883), `profile_identity`=extract_profile_identity, `coordinate_fallback`={"switcher":(540,150)}) → `open_account_switcher(adapter)` → `list_accounts(xml)` → tên account phải xuất hiện (lọc noise status bar như "80%", "17:41")



## ⚠️ PASS giả — không được ghi khi không có màn password (user phạt 2026-08-16, máy 57)

Flow reg email-only/OTP **KHÔNG có màn nhập password TikTok** — nhưng script vẫn tự `make_tiktok_password()` và ghi PASS vào tracking. **SAI**: PASS chỉ thật khi account nhập qua màn password. Cách phân biệt trong log:

- `[8] Fill password` + `✓ password field: found 1 EditText` = **CÓ màn pass** (máy 38/54/66)

- `[pw] TikTok password: ...` rồi `→ Không có màn password (flow email-only / OTP), bỏ qua` = **PASS GIẢ** (máy 57)

Account email/OTP vẫn login OK trên máy (verify qua switcher) nhưng cột PASS là giả → **báo user xử lý** (xóa PASS hay giữ), không âm thầm để pass giả trong workbook.



## Change pass TikTok — module có sẵn (2026-08-16, máy 57 derekbwpt78)

- File: `D:\Taadaa\tiktok-log-in\login_runner\password_change.py` (workflow, generate_password, classify, CLI — KHÔNG có `if __name__=="__main__"` → gọi `python -c "import login_runner.password_change as pc; pc.main([...])"`)

- Env bắt buộc: `TIKTOK_PASSWORD_WORKBOOK` (workbook tracking), `TIKTOK_F2A_PROVIDER_ROOT` = `D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner` (**SUBDIR python_runner, KHÔNG phải repo root** — code check `f2a_root/"core"/live_phase_b_adapter.py`; root sai → `F2A_REFERENCE_NOT_FOUND`), `TIKTOK_REG_PROVIDER_ROOT` = `D:\Taadaa\Tiktok_Reg`

- `--rows 453` = đúng 1 row; `--machines 57` = CẢ MÁY (kéo theo acc khác CÓ pass — phammai1805 row 450, chỉ muốn 1 acc thì dùng --rows); luôn `--plan-only` trước để xem target

- `--allow-live-password-change` bắt buộc cho đổi thật; `--password-length 12-20` (default 16)

- Script tiện: `scripts/run_password_change.py` (skill này) — tự set sys.path + env, gọi `pc.main()` (module không có `__main__`)

- ⚠️ **Module KHÔNG chụp ảnh proof khi SUCCESS** — JSON chỉ có `proof: "password_changed_and_reopen_verified"`, journal dir RỖNG, `capture_failure` chỉ chụp khi FAIL. Verify thật sau: mở TikTok máy → màn `I18nSettingManageMyAccountActivity` (Manage My Account) + login lại bằng pass mới

- PASS mới được ghi workbook tự động (backup `*.password-backup.xlsx` trước write) — verify row sau khi chạy



## Workbook save dưới lock Excel/OneDrive (2026-08-16)

- `wb.save()` có thể FAIL IM LẶNG khi Excel đang mở file (EXCEL.EXE tồn tại, không có lock file) — đọc lại VẪN giá trị cũ dù save "thành công"

- Fix: `wb.save(tmp)` rồi `os.replace(tmp, tracking)` với retry `PermissionError` (bypass lock, verified)

- Không kill Excel (mất dữ liệu chưa lưu) — dùng os.replace



## Row mới reg ghi LỆCH CỘT (2026-08-16, row 453)

- Row mới từ tracking write có thể đặt **giá trị NGÀY vào cột `device ID`** (col 10) thay vì serial (`16/08/2026` thay vì `ce11160b54ee2f3403`) — verify từng row mới: `device ID` phải là serial thật, PASS đúng trạng thái (trống nếu không qua màn pass)

- Sửa lệch cột cùng lúc với xóa PASS giả



## User workflow preference (2026-08-16, ép nhiều lần)

- **QUY TẮC KHO GMAIL CLEAN V2, STATUS COLS & CHECK-LIVE (User update 2026-08-25 & 2026-08-26)**:
  - `gmail_clean_v2.xlsx` là **KHO MAIL DUY NHẤT (Single Source of Truth)** lưu toàn bộ Gmail/Hotmail của farm.
  - Cấu trúc có thêm 2 cột trạng thái tiếng Anh ở cuối:
    - Cột 11: `info_changed` (đánh dấu `1` khi đã đổi pass / thông tin bảo mật Hotmail).
    - Cột 12: `app_logged_in` (đánh dấu `1` khi đã đăng nhập vào app Outlook trên điện thoại).
  - **Quy tắc chèn hàng (User rule 2026-08-26)**: **TUYỆT ĐỐI CẤM** nhét/nạp dồn cục các tài khoản mới mua xuống đáy bảng `gmail_clean_v2.xlsx`. Nạp cho máy nào phải chèn đúng nhóm hàng của máy đó (sắp xếp tăng dần theo `Số Máy` cột 1 từ Máy 1 -> Máy 80).
  - Hotmail mới mua về nạp thẳng vào `gmail_clean_v2.xlsx` (để trống 2 cột trạng thái). Script reg TikTok tự quét mail chưa có trong `taikhoan_dat_v2_updated .xlsx` để đăng ký.
  - **Quarantine Mail Lỗi**: Nếu Hotmail/Gmail bị lỗi token, die hoặc không lấy được OTP, bắt buộc XÓA khỏi `gmail_clean_v2.xlsx` và lưu vào `D:\Taadaa\Hotmail\hotmail_failed_quarantine.txt` kèm lý do lỗi để gửi khiếu nại shop.
  - **Mua Hotmail BoxTaiKhoan & Lấy lại token gốc qua Chrome Debug (2026-08-26)**:
    - Mua từng acc `amount=1` qua API để nhận trực tiếp mảng `data` JSON token 457 ký tự chuẩn; test `exchange_refresh_token` hợp lệ 100% trước khi nạp vào sheet.
    - Nếu token bị lỗi hoặc bị cắt ngắn, khởi động Chrome người dùng (Profile Kal) với cờ `--remote-debugging-port=9222`, truy cập `https://boxtaikhoan.com/product-orders/` để trích xuất nguyên vẹn dữ liệu từ `textarea.account-field` hoặc `input[data-checkbox]` của từng đơn hàng.
  - **CẤM MỞ APP OUTLOOK**: 100% tài khoản có token Graph API phải đọc mã OTP và Magic Link trên PC, tuyệt đối không mở app Outlook trên thiết bị. Kể cả khi timeout hay TikTok chuyển sang magic link, script chỉ mở deeplink qua intent Android, không bao giờ bật app Outlook trên máy.
- **LỌC PACKAGE XML TIKTOK BẮT BUỘC (2026-08-23)**:
  - UI XML dump từ uiautomator luôn chứa các node của `com.android.systemui` (thông báo "Google Play: Yêu cầu đăng nhập", "Không có điện thoại nào", pin, giờ...).
  - Mọi hàm tìm text / node / login modal bắt buộc phải lọc theo package TikTok (`_iter_package_nodes` / `_tiktok_flat_xml`) để tránh nhận nhầm thông báo hệ thống thành màn hình đăng nhập TikTok.
- **CHẠY SUBSET N MÁY BẰNG TIKTOK_REG_SKIP_STTS (2026-08-23)**:
  - Khi user yêu cầu chạy một subset N máy (không chạy toàn bộ target phát hiện), truyền biến môi trường `TIKTOK_REG_SKIP_STTS="<list STT bỏ qua>"` khi gọi `_run_all_targets.py`.

- **TỰ ĐỌC ẢNH VÀ CHẨN ĐOÁN TRƯỚC KHI BÁO CÁO (User correction 2026-08-18)**:
  - Gửi ảnh qua `MEDIA:<path>` BẮT BUỘC phải dùng `vision_analyze` / tự đọc kỹ chi tiết trên ảnh TRƯỚC khi gửi cho user (CẤM gửi ảnh mà không phân tích kỹ nội dung, để user phải chỉ ra lỗi như bấm nhầm điều khoản dịch vụ).
  - Kiểm tra xem nút bấm có bị tap trúng disclaimer text ("Bằng việc tiếp tục... đồng ý với Điều khoản Dịch vụ") thay vì nút "Tiếp tục" / "Tiếp theo" thật sự hay không.

- **CHẠY SONG SONG TOÀN BỘ MÁY (User correction 2026-08-18)**:
  - Khi user lệnh "chạy reg tiktok các máy đó luôn đi", PHẢI kích hoạt chạy batch đồng loạt toàn bộ các máy mục tiêu (`_run_all_targets.py --full-scope-takeover`), CẤM TUYỆT ĐỐI dừng chờ 1 máy hay chạy lẻ tẻ từng máy làm chậm tiến độ toàn farm. Các máy hoàn toàn độc lập.

- **MỖI bước gửi ảnh → user duyệt → mới chạy bước tiếp**; bước nào bấm không qua → **gửi ảnh LIỀN**, không tự đoán tọa độ lòng vòng ("bước nào m bấm k qua đc liền thì phải gửi ảnh liền cho tao đc k")

- Mọi fix tay → handle vào script + test NGAY (làm tới đâu handle tới đó; user: "mọi rule mọi skill vô dụng vs mày à" khi làm tay không lưu)

- Trả lời câu hỏi của user về script ("script có cách qua bước này r mà?") → **đọc code + trả lời đúng/sai kèm chứng cứ** (có handler nhưng bounds sai — chỉ ra)

- Reg giữa chừng → `--resume` tiếp từ trạng thái hiện tại, KHÔNG chạy lại từ đầu (user: "K chạy lại reg từ đầu. Chạy tiếp hàm ở trạng thái hiện tại")

- CẤM bật auto-rotate (user căm thù) — luôn re-lock trước mỗi lần mở app



## Deferred tracking write — BẮT BUỘC apply sau batch (learned 2026-08-16, máy 54)

`_run_all_targets.py` luôn chạy child với `--defer-tracking-write`: máy SUCCESS chỉ ghi

**JSON** `tracking_result_stt<N>_<email>.json` vào

`artifacts/runs/social-batch-all/<ts>/batch_1/stt_<N>/`, KHÔNG ghi workbook

(`workbook_write: NOT_ATTEMPTED_BY_LOCAL_LAUNCHER`). Log "✅ SUCCESS" KHÔNG có

"saved row" là DẤU HIỆU bị defer. Sau batch phải apply JSON vào workbook —

chạy script `scripts/apply_deferred_tracking.py` (skill này) cho từng JSON:

PASS MAIL=col7) → verify 4 row đủ. JSON chứa sẵn `tracking_row`/`tik` — dùng

trực tiếp, không cần re-lookup.



## Magic-link flow (OTP fail nhiều → TikTok TỰ ĐỔI sang magic-link, live máy 75 2026-08-17)



Khi TikTok gửi OTP thất bại nhiều lần, hệ thống **tự chuyển sang magic-link**: màn "Kiểm tra hộp thư của bạn" / "Bạn có thể đăng ký bằng liên kết được gửi đến `<email>`" + nút "Gửi lại email". KHÔNG phải lỗi — là cơ chế TikTok (user: "Đổi qua magic link là vì thất bại gửi otp nhiều quá hệ thống tiktok tự đổi"). Build như **fallback luôn**, không coi là nhánh hiếm.



- **Detect** (trong `handle_tiktok_email_otp` [7c] + `handle_post_auth_screens` [8b]): flat markers `kiem tra hop thu` / `dang ky bang lien ket` / `sign up with a link` / `gui lai email`

- **Mail magic-link subject** = "Hoàn tất đăng ký bằng cách xác minh email của bạn" — **KHÔNG chứa "tiktok"** → marker lọc cũ (`_TIKTOK_SUBJECT_MARKERS` không dấu) loại mail → URL None. Fix: thêm marker **CÓ DẤU** ("hoàn tất đăng ký", "xác minh email của bạn", "kiểm tra hộp thư", "nhấp vào liên kết") — `normalize_text` không đổi `đ`→`d`

- **URL nằm trong href HTML** (`https://www.tiktok.com/ucenter_web/deeplink/email_verification?...`) — `_strip_html` bỏ thẻ `<a>` nên text body không còn URL; phải regex href từ **raw HTML**, không từ text đã strip

- **Mở URL bằng `am start -a VIEW` = SAI** (thử 2026-08-17): Chrome chiếm foreground → script tưởng "đã rời màn magic-link → OK" (false positive) nhưng TikTok VẪN màn "Kiểm tra hộp thư" — mở Chrome không xác nhận được đăng ký

- **Cách đúng**: mở URL → Android Resolver "Mở bằng" (TikTok / Samsung Internet) → chọn **TikTok + "CHỈ MỘT LẦN"** → TikTok mở CommonFlowActivity. Nếu link hết hạn: "Cuộc hội thoại đã hết hạn, vui lòng đăng nhập lại" + màn "Nhập mã gồm 6 chữ số" → cần OTP mới qua "Gửi lại mã"

- **Link hết hạn ~20 phút** ("Liên kết có hiệu lực trong 20 phút" trong mail): loop dài làm mail chết → **chạy lại reg từ đầu** lấy mail mới (user: "chạy quá lâu mail hết valid rồi phải chạy lại từ đầu lấy mail ms")

- **Trong Outlook app, magic link = nút ĐỎ "[Xác minh email]"** (không phải link text trong body): reader tìm link text → fail `INBOX_LOST_DURING_MAGIC_LINK_READ`. Fallback `find_text_tap("Xác minh email","Xac minh email","Verify email")`. ⚠️ `adb input tap` theo bounds XML **KHÔNG ăn** trên nút WebView (Reading Pane intercept) — phải tap qua **ATX-first** (`find_text_tap` dùng `get_ui_xml` = ATX primary; user nhắc lại 2026-08-17: "Lại dùng uiautomator t nhắc đi nhắc lại dùng atx trc r mà" — **CẤM đề xuất "uiautomator click"**, uiautomator chỉ fallback); nút thật = node `resource-id="link"` clickable (bounds lệch với node text tiêu đề "Xác minh email của bạn" — đừng nhầm, node text có bounds khác). ⚠️⚠️ **WebView không expose XML node `link` (máy 75 22:16, commit `67443c8`):** UI XML trong reading pane Outlook có lúc chỉ 9KB và không có bất kỳ node con nào của WebView → `_atx_click_link_button` phải có fallback **ATX click trực tiếp vào tọa độ tâm nút đỏ `(540, 1460)`** (portrait 1080x1920) khi không parse được XML.
- **Graph API Deeplink Extraction + ResolverActivity (Phương án 2 verified 22:34):** Trích xuất deeplink URL trực tiếp từ token Graph API (`read_tiktok_magic_link_from_graph_token` → URL chứa `email_verification?code=...`) → mở qua `am start -a android.intent.action.VIEW -d "<url>"` → Android bật dialog "Mở bằng" (ResolverActivity) với TikTok được chọn sẵn → tap **"CHỈ MỘT LẦN"** tại `(570, 1818)` → TikTok mở thẳng và loading spinner xác thực token.
- **`wait_login_success` false positive (commit `8843ca2`):** `success_hints` CẤM chứa `"Hộp thư"` / `"Hop thu"` vì sẽ match nhầm màn hình *"Kiểm tra hộp thư của bạn"* (màn đang chờ verify magic-link) → script tưởng đã đăng nhập thành công rồi tap nhầm nút "Gửi lại email" làm tab Profile → STOPPED.
- **Màn "Tạo tài khoản" nhập email bị nhầm `login_popup` (commit `3186564`):** Màn hình đăng ký có dòng *"Chuyển sang dùng số điện thoại"* chứa cụm "so dien thoai" → classifier `_post_auth_ui_state` nếu check login markers trước sẽ nhầm thành `login_popup` và tìm nút "Tiếp tục với email" (không tồn tại) → STOPPED. Fix: state `signup_email_form` (`dia chi email` + `chuyen sang dung so dien thoai`) phải check TRƯỚC `login_popup`.
- `read_tiktok_magic_link_from_outlook_app` RAISE exception (LoginBlocked) thay vì trả None → `if not code:` recovery không bao giờ chạy; phải bọc try/except (`_read_magic_link_with_inbox_recovery`): mở app → tap "Hộp thư đến" (badge "Hộp thư đến (1)") → reader lần 2 → fallback tap nút Xác minh email
- Reader CÓ THỂ TREO VÔ HẠN (blocking, máy 75 kẹt 1.5h — không trả về cũng không throw → recovery không tới). **FIX ĐÃ LAND (commit `9bea46c`, verify live 17/08 log `✓ tap nút 'Xác minh email' (ATX) → magic link OK`):** `_read_magic_link_with_inbox_recovery` **ATX-first** — mở Outlook → tap nút Xác minh email NGAY (find_text_tap) → chưa thấy nút thì tap 'Hộp thư đến' → mở mail TikTok (find_text_tap 'TikTok') → tap nút → canonical reader chỉ gọi CUỐI CÙNG (không chờ nó)

- ⚠️ **`magic link OK` sau tap nút = FALSE POSITIVE (máy 75, 15:39-15:44):** tap đăng ký thành công trên node nhưng **link KHÔNG thực sự kích hoạt** — foreground vẫn `com.microsoft.office.outlook` (WebView Reading Pane nuốt tap), TikTok không nhảy màn → script tưởng xong rồi quay lại [7c] đọc OTP vô hạn. PHẢI **verify thật sau tap**: `mResumedActivity` = TikTok (`com.ss.android.ugc.trill`) hoặc màn magic-link biến mất khỏi dump — nếu không, không return "MAGIC_LINK". Hướng chắc chắn hơn khi link còn hiệu lực (≤20 phút): **Graph URL → `am start -a VIEW` → Resolver "Mở bằng" → chọn TikTok + "CHỈ MỘT LẦN"** (verify 15:04: TikTok mở CommonFlowActivity thật).\n- **Resume branch Outlook-foreground (commit `ff15f1b`):** resume thấy `com.microsoft.office.outlook` foreground (reader lần trước để lại) → gọi thẳng `_read_magic_link_with_inbox_recovery` thay vì bỏ qua (trước: package=other → PENDING)\n- **Popup feedback Outlook chặn list mail** (máy 75, 15:30): "Chúng tôi muốn lắng nghe phản hồi của bạn — KHÔNG, CẢM ƠN / CHẮC CHẮN" xuất hiện đầu Inbox → intercept tap vào mail TikTok → reader treo. PHẢI dismiss popup (tap 'KHÔNG, CẢM ƠN') trước khi find_text_tap('TikTok')\n- Chi tiết session đầy đủ: `references/magic-link-flow-20260817.md`
- Recovery batch, lock-root integrity, OTP/password field guard và evidence checklist: `references/batch-recovery-and-locks.md`



- **Fresh Machine Login Sheet Bypass (2026-08-18 máy 75)**:
  - Khi máy mới tinh chưa có tài khoản TikTok mở app, TikTok không hiển thị tab Hồ sơ mà bật ngay login modal / bottom sheet `I18nSignUpActivity` ("Số điện thoại / Đăng nhập / Tiếp tục với email / Tạo tài khoản").
  - `register()` phát hiện `has_login_modal` kết hợp `not _is_personal_profile_screen_xml()` để xác định `_is_fresh_signup = True` -> bypass các bước `go_to_profile` / `open_account_dropdown` / `tap_add_account` và đi thẳng vào `choose_email_login`.
  - Giúp tránh lỗi kẹt `STOPPED: [02_profile] Khong vao duoc tab Ho so/Profile`.

- **OTP 6 ô - CẤM dùng AdbKeyboard broadcast (`sensitive=True`) cho OTP field (2026-08-18)**:
  - Màn hình "Nhập mã" (6 ô OTP visual bên trong 1 EditText lớn) nếu dùng `type_into_node(..., sensitive=True)` sẽ phát `ADB_KEYBOARD_INPUT_TEXT` qua AdbKeyboard. Tuy nhiên khi bàn phím mặc định Samsung (`SamsungKeypad`) đang mở, broadcast này không ăn vào ô nhập liệu -> 6 ô OTP bị trống -> script timeout.
  - **Fix:** Phải dùng `sensitive=False` (`input text <code>` / direct text) để điền thẳng mã OTP vào ô sau khi tap focus.

- **Bấm nhầm Disclaimer Điều khoản dịch vụ khi Submit Email (2026-08-18)**:
  - Trên màn nhập Email / Login, văn bản điều khoản *"Bằng việc tiếp tục với tài khoản có vị trí tại Việt Nam, bạn đồng ý với Điều khoản Dịch vụ..."* có thể bị `find_text_tap` khớp nhầm thành "Tiếp tục" do chứa cụm "tiếp tục".
  - **Fix:** Phải lọc bỏ triệt để các node chứa "dieu khoan" / "quyen rieng tu" khi tìm nút bấm submit email, chỉ tap đúng nút `Button` ("Tiếp tục" / "Tiếp theo" / "Đăng nhập") thực tế.

- **Nhận diện Profile cá nhân vs Home Feed (2026-08-18)**:
  - Màn hình cá nhân có bottom nav chứa tab "Trang chủ" dễ bị `_is_home_feed_xml` nhận nhầm thành Home Feed.
  - **Fix:** Phải guard nếu có các markers màn hình cá nhân ("them tieu su", "sua ho so", "anh ho so"...) thì `_is_home_feed_xml` trả về `False` để đi đúng nhánh mở Switcher -> Thêm tài khoản.

- **Batch Reg Runner `_run_all_targets.py` & Target Inventory Preflight (2026-08-18)**:
  - Chạy batch toàn bộ máy: `env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe _run_all_targets.py --full-scope-takeover`. Có thể filter qua env `TIKTOK_REG_SKIP_STTS="2,34,..."`.
  - **Lỗi `TARGET_INVENTORY_CONFLICT` / `TARGET_INVENTORY_MISSING_SERIAL`**: Nếu file `taikhoan_run_safe.xlsx` sheet `Accounts` có dòng bị gán nhầm ngày tháng vào cột Device ID hoặc rỗng serial -> `_detect_clean.py` fail closed ngay lập tức. Phải audit và điền đúng serial per machine trong `taikhoan_run_safe.xlsx` trước khi chạy batch.
  - **Khóa máy (Device Lock)**: Kiểm tra các lock file tồn tại trong `C:\Users\Kibe\.codex\device-locks\` (vd từ `vi_changer_runner.py`). `_run_all_targets.py` sẽ bỏ qua các máy bị khóa trừ khi có cờ `--full-scope-takeover` hoặc lock đã được giải phóng.

- **Quy tắc vận hành khi user yêu cầu chạy reg TikTok (User correction 2026-08-18)**:
  - Khi user lệnh "chạy reg tiktok các máy đó luôn đi", phải kích hoạt chạy batch đồng loạt trên toàn bộ các máy đã log Hotmail (`_run_all_targets.py`), không chạy lẻ tẻ từng máy 1 làm chậm tiến độ.
  - **Lock máy khi chạy trên thiết bị (User rule 2026-08-31)**: BẮT BUỘC giữ và kiểm tra device lock (`C:\Users\Kibe\.codex\device-locks\`) trước và trong khi chạy thao tác trên máy thật; nhả lock sạch sẽ sau khi hoàn thành.
  - **Tự động đóng Pop-up Gmail & Bật Auto-Sync khi đọc OTP (2026-08-31)**:
    - Bật `settings put global auto_sync 1` và `master_sync 1` trước khi mở hòm thư.
    - Xử lý triệt để các popup/banner cản trở: "Tăng cường khả năng bảo vệ trước hành vi lừa đảo" (tap "Không, cảm ơn"), "Tính năng tự động đồng bộ hóa đang tắt" (tap "Bật" / "Bỏ qua"), tooltip "Nhấn vào hình ảnh người gửi..." (tap "Bỏ qua"), Meet banner.
    - Fallback: Khi chờ OTP Gmail bị timeout, tự động gọi module `check_google_account_health_from_gmail` để phân loại Google Account LIVE vs dính CAPTCHA/relogin, không fail cứng.
  - **Fallback Hotmail Graph API -> Outlook App (2026-08-31)**:
    - Ưu tiên đọc OTP / Magic link qua Graph API trên PC; nếu timeout, tự động fallback mở Outlook app trên máy (nếu có mật khẩu).

- **Workflow chuẩn khi xử lý Magic-link trong Outlook (bắt buộc, user rule 17/08)**:
  1. Chỉ được vào Outlook -> tìm đúng mail TikTok MỚI NHẤT -> bấm nút "Xác minh email" (qua ATX click, node `resource-id="link"` clickable).
  2. Bấm link thành công thì link sẽ **TỰ ĐỘNG MỞ APP TIKTOK**.
  3. **TUYỆT ĐỐI CẤM** tự mở app TikTok bằng intent/`monkey` (như logic `non-TikTok foreground -> resume TikTok` cũ) vì sẽ làm bypass luồng xác thực, app nhảy về màn login/password chưa được verify.
  4. Phải phân biệt rõ ràng:
     - Màn Magic-link ("Kiểm tra hộp thư của bạn", "đăng ký bằng liên kết", nút "Gửi lại email")
     - Màn OTP số ("Nhập mã gồm 6 chữ số", 6 ô input, nút "Gửi lại mã")
     - Xóa bỏ `"Hộp thư"/"Hop thu"` khỏi `success_hints` của `wait_login_success` để tránh false-positive match nhầm màn "Kiểm tra hộp thư".
  5. Đối với popup "Ghi chú nhanh về tài khoản Microsoft / Inapp UnifiedConsent": XML không expose text tiếng Việt, phải match marker `inapp unifiedconsent` hoặc bắt qua capture ảnh + bấm nút OK tại (540, 1704).
  6. Khi chuyển luồng signup -> không để màn "Tạo tài khoản" nhập email (có link "Chuyển sang dùng số điện thoại") bị state-classifier nhận nhầm thành `login_popup`.
  7. **CẤM Force-stop / Đóng app TikTok khi đang chờ Magic-link (Root cause 2026-08-17 22:53):** Khi mở magic-link từ trình duyệt/ngoài app, TikTok báo lỗi *"Đã xảy ra lỗi. Hãy đảm bảo sử dụng cùng thiết bị bạn đã sử dụng để gửi email xác minh."* NGUYÊN NHÂN: Khi kill/force-stop hoặc đóng Task của TikTok, session ticket/cookie đăng ký trong RAM của `SignUpOrLoginActivity` bị hủy. Khi link kích hoạt, TikTok mở phiên mới không khớp ticket -> từ chối. **BẮT BUỘC:** App TikTok phải được GIỮ NGUYÊN chạy nền ở đúng màn hình *"Kiểm tra hộp thư của bạn"* trong suốt quá trình xác thực email.
  8. **Image-Driven Step Verification:** Khi gặp màn hình UI phức tạp hoặc WebView nuốt XML, sử dụng screencap + Vision API để phân tích màn hình, xác định tọa độ chính xác thay vì phụ thuộc hoàn toàn vào UI XML dump dễ bị thiếu node.
  9. **Date Picker Focus & Continue Button Tap (2026-08-17 máy 78):**
     - Nút "Tiếp tục" của màn hình Date Picker có bounds `[96, 1704][984, 1872]` -> phải tap đúng tâm `(y1 + y2) // 2 = 1788` (trước bị bug `y1 + 24 = 1728` chạm vào mép trên bị trượt).
     - Ưu tiên bấm qua ATX JSON-RPC (`_atx_click`) trước khi fallback sang `input tap`.
  10. **Lỗi "Nhập đúng mã PIN" / OTP hết hạn (2026-08-17 máy 78):**
     - Khi TikTok báo lỗi "Nhập đúng mã PIN" hoặc mã OTP cũ hết hạn, màn hình DatePicker bị chặn không cho bấm "Tiếp tục".
     - **Fix:** Phải tự động phát hiện marker `nhap dung ma pin` / `invalid code` -> tap nút "Gửi lại mã" (`rid=ktj`) -> lấy mã OTP mới từ Graph API -> điền mã mới để mở khóa màn hình Ngày sinh.
  11. **Workbook Permission Lock (2026-08-17):**
     - Khi `gmail_clean_v2.xlsx` bị mở trong Excel trên máy host, Graph token reader bị `PermissionError` [Errno 13] -> tưởng là không có token rồi fallback sang Outlook app sai hướng. Phải đảm bảo file workbook không bị khóa process hoặc đóng Excel trước khi chạy.
  - **Bảo toàn IP & Proxy khi Reg hàng loạt (2026-08-18)**:
    - CẤM chạy reg nhiều máy trên cùng 1 Direct IP (không proxy) vì TikTok sẽ flag rate limit ngầm: ép đổi từ OTP sang Magic Link, chặn nhận PIN dù nhập đúng ("Nhập đúng mã PIN"), hoặc chặn nút Tiếp tục ở DOB. Mỗi máy reg BẮT BUỘC phải gán và kết nối Proxy/VPN (Vi Changer) riêng trước khi reg.
    - Khi ViChanger bật nhưng proxy dead/unreachable (`GET_IP` failed sau 3 lần retry dù có interface `tun0`), preflight fail-closed chặn ngay lập tức (`VPN_PREFLIGHT_BLOCKED`) để bảo vệ farm, không được tự ý bypass. Cần kiểm tra lại proxy/ViChanger trước khi chạy tiếp.
  13. **Đóng Recent Apps ("ĐÓNG TẤT CẢ") khi Reset flow (2026-08-18):**
     - Khi reset flow hoặc chuẩn bị chạy lại từ đầu: mở Recent Apps (`keyevent 187`) -> tap nút "ĐÓNG TẤT CẢ" `(540, 1830)` để giải phóng toàn bộ task nền (TikTok, Outlook, Chrome) rồi mới đưa máy về HomeScreen sạch sẽ.
  14. **BẮT BUỘC FLOW LOGIN CHUẨN (User correction 2026-08-18):**
     - CẤM tự ý click vào "Tạo tài khoản" ở bottom sheet hay form đăng ký trực tiếp (`signup_entry`).
     - Quy trình chuẩn 100% bắt buộc: Tab Hồ sơ -> Đăng nhập -> "Tiếp tục với email/tên người dùng" -> Nhập email chưa reg -> TikTok tự phát hiện "Chưa có tài khoản" và bật dialog "Tạo tài khoản mới" -> Chuyển tiếp sang OTP. Mọi hành vi tự chế form đăng ký đều vi phạm và làm hỏng bộ phân loại trạng thái (classifier).
  15. **Anti-detect Jitter & VPN Preflight (Port 2026-08-18 từ main sang reg-stable-0722):**
     - Mọi thao tác `tap()` và `swipe()` tự động áp dụng `_jitter(coord, max_offset=6)` (±4-6px) ngẫu nhiên để chống TikTok phát hiện gesture bot deterministic. 100% swipe calls đều đi qua helper `swipe()`.
     - `preflight_phase` tích hợp `resolve_proxy_mapping_path()` + `require_android_vpn` kiểm tra bắt buộc kết nối VPN/Vi Changer trên các máy có gán proxy trong mapping, fail-closed an toàn (không dùng generic exception nuốt lỗi).
  16. **Quy tắc Branch Git TikTok_Reg & Audit Routing (2026-08-18):**
     - Nhánh canonical vận hành live duy nhất của farm là `reg-stable-0722` (chứa toàn bộ logic Hotmail, Graph Token OTP, Magic Link, DOB fix, Anti-detect Jitter, VPN Gate).
     - CẤM tự ý force-push hoặc ghi đè `main`/`master` cũ khi chưa port và audit đầy đủ tính năng.
     - **Quy tắc Audit chuẩn**: CẤM dùng `delegate_task`/Flash để audit; bắt buộc gọi qua 9Router combo `plan-review` (`gpt-5.6-terra`) hoặc `plan-review-hard` (`gpt-5.6-sol`), fallback sang Claude CLI (`claude -p`).
  17. **Ưu tiên đọc OTP qua Graph API Token & CẤM MỞ APP OUTLOOK (User rule update 2026-08-25):**
     - Mailbox có `refresh_token` + `client_id` (Hotmail loại 2) BẮT BUỘC 100% đọc mã OTP và Magic Link URL thẳng từ Microsoft Graph API trên PC.
     - **TUYỆT ĐỐI CẤM** mở app Outlook trên thiết bị khi mailbox đã có token. Kể cả khi TikTok chuyển sang luồng Magic Link hoặc timeout OTP, script chỉ đọc token trên PC và mở deeplink xác thực qua `am start VIEW`, không bao giờ bật app Outlook trên máy.
     - CHỈ duy nhất trường hợp mailbox hoàn toàn không có token (Hotmail loại 1) mới được fallback mở app Outlook.
     - ⚠️ **PITFALL BẢO TOÀN ĐỘ DÀI TOKEN (2026-08-25)**: Chuỗi `refresh_token` OAuth2 của Microsoft dài 450-525 ký tự. Bắt buộc test `exchange_refresh_token` thành công 100% trước khi nạp vào sheet, tránh token bị cắt ngắn dẫn đến HTTP 400 AADSTS70000 làm script fallback nhầm sang mở Outlook app.
  - **Quy tắc đặt Display Name & Nickname (@handle) Việt hóa (User rule 2026-08-25)**:
    - Tên hiển thị (Display Name): Random đa dạng theo 5 phong cách người dùng thật:
      1. Họ + Đệm + Tên (VD: *Trần Minh Đạt, Nguyễn Hoài An, Lê Thu Trang*).
      2. Họ + Tên (VD: *Nguyễn Nam, Lê Linh, Vũ Phong*).
      3. Đệm + Tên (VD: *Ngọc Linh, Thanh Thảo, Khánh Vy, Hoài An*).
      4. Tên + Biệt danh đời thường (VD: *Linh Bông, Đạt Còi, Vy Miu, An Kem, Nam Sóc, Phong Dâu*).
      5. Tên lặp / Duo dễ thương (VD: *An An, Gạo Gạo, Miu Miu, Nhím Nhím, Bơ Bơ*).
    - Biệt danh (@username/handle): Chế theo tên không dấu + số đuôi tự nhiên (`@nguyen9490`, `@an_kem24`, `@linh.bong123`...).
  19. **Cleanup sau khi Reg thành công (User rule 2026-08-18):**
     - Ngay sau khi reg hoàn tất thành công và lưu dữ liệu (hoặc ghi deferred tracking JSON), script bắt buộc gọi helper `_post_reg_cleanup(device_id)`: thực hiện `am force-stop com.ss.android.ugc.trill` và gửi `KEYCODE_HOME` (`input keyevent 3`) để đưa máy về Home Screen sạch sẽ, giải phóng RAM và tránh treo UI.
  20. **Cooldown 2 ngày khi dính Rate Limit "Truy cập dịch vụ quá thường xuyên" (User rule 2026-08-26):**
     - Khi TikTok chặn với thông báo *"Bạn truy cập dịch vụ của chúng tôi quá thường xuyên"* / *"Too many attempts"* / *"Too many requests"*:
     - **TUYỆT ĐỐI CẤM** cố reg lại máy đó ngay lập tức (sẽ làm TikTok kéo dài thời gian phạt hoặc block vĩnh viễn thiết bị/IP).
     - **Quy tắc Cooldown 2 ngày (48h)**:
       - Máy dính lỗi rate limit bắt buộc phải được đánh dấu cooldown trong `D:\Taadaa\runtime\kibe\device_cooldowns.json` với `cooldown_until = now + 48 hours`.
       - Bộ lọc `_detect_clean.py` khi quét target phải tự động bỏ qua (SKIP) các máy đang trong thời gian cooldown (`STT=<N>: COOLDOWN_ACTIVE`).
       - Máy chỉ được phép nạp/reg lại sau khi đã qua đủ 2 ngày nghỉ ngơi.
     - **Thuật toán xử lý lỗi phân tầng (User rule 2026-08-26)**:
       - Các lỗi cơ học/UI nhẹ (timeout nút Tiếp tục, picker DOB chậm, chưa tap OTP lần 2, chưa đóng dialog sau auth, popup chọn bàn phím Android đè màn hình, OTP hết hạn cần bấm 'Gửi lại mã'): Agent **BẮT BUỘC TỰ ĐỘNG XỬ LÝ** (bấm gửi lại mã, giải phóng popup, re-fetch OTP qua Graph API hoặc chạy lại từ đầu). Khi fix thành công thì tự động handle vào script.
       - **CHỈ KHI THẬT SỰ KẸT / GẶP MÀN LẠ CHƯA TỪNG THẤY** (Captcha không giải được, mất kết nối proxy/ADB vĩnh viễn, block tài khoản bất thường): Mới dừng lại, giữ nguyên lock + màn hình và báo cáo kèm ảnh cho user.
     - **Quản lý tải Batch Reg & Xử lý Pending OTP (2026-08-26)**:
       - Khi chạy batch lớn (40-72 máy song song), các máy xếp hàng sau có thể bị timeout ở bước chờ OTP do nghẽn mạng/API.
       - Sau khi batch lớn kết thúc, quét toàn bộ máy `PENDING` (màn hình OTP 6 số hoặc Profile chưa load kịp): gom lại thành batch nhỏ chạy tuần tự/nhẹ nhàng (concurrency 4-6) để giải phóng nốt toàn bộ tài khoản vào workbook tracking.
  21. **Quy trình triển khai tính năng / Code mới (User rule 2026-08-26):**
     - Mọi tính năng code mới bắt buộc tuân thủ đủ 6 bước khép kín:
       1. Lập Plan `.hermes/plans/YYYY-MM-DD_<name>.md`.
       2. Audit Plan qua 9Router (`gpt-5.6-terra` / `plan-review`) lấy `VERDICT: APPROVED`.
       3. Worker TDD (Red Test trước -> Green Code sau).
       4. Code Review Diff qua 9Router (`gpt-5.6-sol` / `plan-review-hard`) lấy `VERDICT: APPROVED`.
       5. Pytest isolated trên venv.
       6. Pull Rebase & Commit/Push.

- **References**:
  - `references/magic-link-flow-20260817.md` — session máy 75: diễn tiến OTP→magic-link, Graph URL false-positive, Resolver "Mở bằng", hết hạn 20 phút, reader raise/hang, tap nút đỏ.
  - **`tiktok-registration-ops/references/manual-reg-tay-20260820.md`** (sibling skill) — reg TAY khi script kẹt (máy 78): "Tài khoản không tồn tại"→"Tạo tài khoản mới" (300,738); DOB year-picker **swipe chậm 300ms = −3 năm/lần, nhanh 100ms = loạn**; popup "Xem lại ngày sinh"→OK (540,1184)→Tiếp tục (540,1788) lần 2; pass chứa `$` bị bash nuốt→dùng `# ? ! @` và verify số dấu •; Inapp UnifiedConsent landscape OK (960,865) không ăn→force-stop Outlook + đọc OTP qua Graph; OTP cũ loop trong Gmail→dừng sau 2 lần "Gửi lại mã"; ViChanger `enabled=0`/"No LSPosed access!!!"→block máy; safe workbook ngày lẫn vào cột serial→audit trước `_detect_clean.py`.

