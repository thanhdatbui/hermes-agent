# UI dump STALE ≠ màn hình thật + coordinate fallback + OTP refresh (Tiktok_Reg, máy 34, 2026-08-07 tối)

## 1. uiautomator dump stale — dump trả feed trong khi màn thật profile

- **Triệu chứng**: runner log `profile selected (972,1857)` nhưng dump fail = FEED ("Tây Ninh"/"Bạn bè"); core → `SWITCHER_ANCHOR_AMBIGUOUS` → FINAL_BLOCKED. Lặp nhiều run, kể cả sau reboot.
- **Sai lầm chẩn đoán**: kết luận "máy 34 profile không render" — user chỉ đúng: "là sao profile vẫn bth mà, tất cả các máy cùng 1 phiên bản cùng 1 độ phân giải". Mirroring cho thấy profile yobi @yobi1965 render BÌNH THƯỜNG.
- **Bài học cứng**: khi dump ≠ kỳ vọng, VERIFY bằng `screencap -p` + vision (không cần uiautomator) TRƯỚC khi kết luận máy/app lỗi. Dump stale (E=137 hoặc nội dung cũ "Tây Ninh") = lỗi TRANSPORT (atx/uiautomator wedged), KHÔNG phải màn hình sai.
- **Fix dump stale**: `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` + `pkill -9 -f uiautomator` → dump E=0 (core 0.4.43+ có; xem mục 17 reference s7-otp).
- **Sau reboot máy**: (a) LSPosed popup "No LSPosed access !!!" phải tap OK trước khi dump; (b) VPN tun0 phải lên (~60-90s) trước khi mở TikTok; (c) dump khi TikTok đang load → `ERROR: could not get idle state` — chờ feed idle.

## 2. Profile tab coordinate: 1857 → 1883 (clamp)

- **Tap (972,1857) trượt**: tab "Hồ sơ" bounds `[864,1864][1080,1903]` → center (972,1883). 1857 cao 26px TRÊN bounds → TikTok không vào profile → dump vẫn feed.
- **Fix**: `COORD["profile_tab"]` + bottom-right fallback = (972,1883); `_profile_tab_node` clamp `if cy < 1870: cy = 1883` (dump node bounds lệch vài px vs tap thật).
- **Bài học**: coordinate cứng trong COORD phải verify bằng bounds thật từ dump + screenshot. Cùng model/resolution nhưng dump node bounds có thể lệch — clamp về tọa độ verified (tap tay đúng coord → vào profile, 2 screenshot xác nhận).

## 3. Core hook `coordinate_fallback` — consumer implement, KHÔNG sửa core

- **Core** `open_switcher` (account_switcher.py:679-680) gọi `adapter.coordinate_fallback("switcher")` khi semantic/image anchor unavailable (dump stale) — đã wrap `callable(evidence)`.
- **Consumer thiếu hook** → `None` → `SWITCHER_ANCHOR_AMBIGUOUS`. Fix: implement `coordinate_fallback(action)` trong `_SocialAccountSwitcherAdapter` trả (540,150) cho `"switcher"` (verified tap tên user mở dropdown), `None` cho action khác.
- **Test guard cũ**: `test_login_method_entry.py:8` assert `not hasattr(adapter, "coordinate_fallback")` (ngăn consumer override) — BREAK khi thêm hook. Audit longcat bắt P0 này. Sửa thành `hasattr` + test 2 case (`"switcher"`→(540,150), `"unknown"`→None).
- **Bài học**: khi core fail anchor do dump treo, check core có hook fallback sẵn chưa (`getattr(adapter, "<hook>", None)`) — implement hook consumer (adapter primitive hợp lệ theo AGENTS "consumer may provide adapter primitives") thay vì sửa core. Core side: chỉ thêm docstring contract + unit test (adapter có hook → gọi 1 lần; không hook → vẫn SWITCHER_ANCHOR_AMBIGUOUS, không crash).

## 4. OTP: pull-refresh TRƯỚC fast-path đọc code

- **Bug**: fast-path đọc code từ conversation/preview list capture TRƯỚC `_gmail_pull_refresh(1)` (chạy SAU cả 2 fast-path ~dòng 7143) → mail OTP mới chưa sync → code cũ/không có.
- **Fix (audit longcat MINOR_FIXES F1)**: gọi `_gmail_pull_refresh(1)` ngay sau `_ensure_gmail_mailbox("after account switcher")` TRƯỚC mọi fast-path; bỏ fast-path 1 (conversation capture cũ trước khi vào mailbox); giữ refresh 2 (idempotent).
- **Pitfall**: `_gmail_pull_refresh` def nằm SAU chỗ gọi → NameError bị nuốt trong `except Exception` → "refresh chạy nhưng chưa bao giờ chạy thật". Kiểm tra def order khi gọi hàm lồng nhau (nested function trong flow).

## 5. Magic link vs OTP — tùy lúc (user: "tuỳ lúc có lúc gửi otp")

- TikTok chọn kênh gửi KHÔNG cố định: lần này OTP 6 số, lần sau magic link.
- Detect màn TikTok "Gửi lại email" / "sign up with a link" / "dang ky bang lien ket" → flow phải vào email, mở mail TikTok ĐẦU TIÊN, bấm link ("Xác nhận"/"Confirm"/"Click here") — không chỉ tìm code 6 số.
- `otp_screen_hints` đã chứa cả marker magic link — đảm bảo khi detect kênh link, fetch ưu tiên mở mail + tap link (xem mục 15a reference s7-otp).

## 5a. BUG CLASSIFY: màn magic-link verify bị nhầm `registered_otp` (2026-08-07, máy 34 — user phát hiện)

- **Triệu chứng**: run "kết thúc sạch" `[07] Tất cả 3 email của STT N đã có TK TikTok` — NHƯNG user hỏi "magic link có bấm chưa mà biết mail đã reg?" → điều tra: MAIL CHƯA BAO GIỜ được bấm link, runner ĐOÁN SAI.
- **Root cause**: TikTok gửi magic link xác minh email mới (chưa đăng ký) hiện màn "Kiểm tra hộp thư của bạn" + "Gửi lại email sau 46 giây" + "Đăng nhập bằng mật khẩu" (dump xác nhận: `debug_34_otp_screen_*.xml` có 3 text này). Nhưng `detect_after_continue` (social_reg_v1.py L1673-1685) gộp `"kiem tra email", "kiem tra hop thu", "gui lai email", "resend email"` vào `otp_hints` → classify `registered_otp` → flow bỏ qua email, không vào inbox bấm link. Fallback unknown (L3639-3644) cũng gộp nhóm này.
- **Phân biệt 2 màn**:
  - REAL_OTP_LOGIN (email ĐÃ có TK): `nhap ma, gui lai ma, resend code, ma xac nhan, ma xac minh, verification code, enter the code, sent a code` → `registered_otp`.
  - MAGIC_VERIFY (email CHƯA có TK, đang xác minh): `kiem tra email, kiem tra hop thu, check your email, check email, gui lai email, resend email` → state MỚI `verify_email_pending`.
  - **PRIORITY**: kiểm tra REAL_OTP_LOGIN TRƯỚC; cả 2 nhóm cùng xuất hiện → `registered_otp` (audit finding 1). Caller nhánh `verify_email_pending` → giữ email + đi vào `handle_tiktok_email_otp` (đã có magic-link path) — KHÔNG bỏ qua.
- **Fallback unknown phải dùng CHUNG split classifier** (không duplicate marker list — audit finding 3; duplicate sẽ drift, tái mở bug).
- **Test bắt buộc**: XML chỉ "Kiểm tra hộp thư của bạn"+"Gửi lại email sau 46 giây" → KHÔNG registered_otp; XML "Nhập mã xác minh" → registered_otp; NEGATIVE: XML có cả 2 nhóm → vẫn registered_otp; "Gửi lại email sau 46 giây" 1 mình → verify_email_pending. UI.md entry kèm state mới + exact UI strings.
- **Bài học chẩn đoán**: khi runner "dừng sạch vì email đã reg" nhưng bạn NGHI ngờ, đừng tin tracking — kiểm tra dump/screenshot màn lúc classify + trace marker nào match. Classifier mù (2 ngữ cảnh dùng chung 1 marker set) là nguồn false-positive "đã có TK".

## 6. Verify core version bằng import với ĐÚNG PYTHONPATH

- **Pitfall**: `pip show automation-core` trả 0.4.40 + Location hermes-agent venv khi chạy KHÔNG có PYTHONPATH → tưởng runner chạy core cũ (sai).
- **Verify đúng**: `env -i PYTHONPATH="D:\...\tiktok-reg-recovery\Lib\site-packages;D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail" python -c "import automation_core, importlib.metadata as m; print(m.version('automation-core'))"` → 0.4.43 (site-packages của runner đã có bản mới).
- **Bài học**: version = import thật với đúng env runner; không tin `pip show` mặc định (nó lấy env hiện tại, có thể là venv khác).

## 7. Worker hết tool-budget giữa chừng / 429 rate limit

- Worker báo cáo trung thực "hết budget, chưa verify" → session verify độc lập diff + pytest (không tin self-report), dispatch lại PHẦN task chưa làm với budget gọn (~30 tool calls: đọc 1 lần, patch 2 chỗ, test 1 lần, báo cáo).
- 429 giữa worker → health check 9router (`curl -X POST http://127.0.0.1:20128/v1/chat/completions` với `Authorization: Bearer $NINEROUTER_API_KEY`) → hồi phục → dispatch lại worker (retry hợp lệ sau rate-limit, không phải lặp lỗi code).
- Worker fail giữa chừng: check `git diff` file đích xem worker đã ghi gì chưa (có thể 0 thay đổi → làm lại từ đầu).

## 7a. Audit transport: opencode CLI treo (0 bytes, timeout) → 9router API trực tiếp model combo `deepseek-v4-flash`

- **Triệu chứng**: `opencode run --model opencode/longcat-2.0-free` treo >9 phút, file jsonl 0 bytes (queue đứng). Lần trước cùng lệnh chạy OK 6 phút — transport không ổn định.
- **Fallback nhanh hơn**: gọi thẳng 9router `POST http://127.0.0.1:20128/v1/chat/completions` với `model: "deepseek-v4-flash"` (combo KHÔNG slash = cmc→oc/free→26 v98, theo memory) + `Authorization: Bearer $NINEROUTER_API_KEY` → verdict APPROVED+MINOR_FIXES đầy đủ findings.
- **Pitfall parse**: model combo trả `reasoning_content` rất dài, `content` rỗng + `finish_reason=length` khi max_tokens nhỏ → chưa tới verdict. Fix: `max_tokens` lớn (5000+) + prompt yêu cầu "ANSWER DIRECTLY IN FINAL CONTENT, NO CHAIN-OF-THOUGHT" + parse tolerant (raw có thể là nhiều JSON object dính nhau — cắt từ `{` cuối cùng có `choices`).
- **Bài học**: khi audit CLI treo, đừng chờ — kill + chuyển transport (opencode CLI → 9router API trực tiếp) là hợp lệ (cùng slot audit, stop ở verdict đầu tiên). Health check 9router trước: `curl -X POST .../chat/completions -d '{"model":"opencode/deepseek-v4-flash-free",...}'` — thiếu Bearer trả `invalid_api_key` nhưng endpoint sống.

## 8. `[07] Tất cả email STT N đã có TK TikTok` — CÓ THỂ là false terminal (xem 5a)

- Khi email thực sự đã có TK (tracking "da co TikTok" đáng tin) → STOPPED đúng quy trình, không phải bug.
- **NHƯNG 2026-08-07 phát hiện: chính kết luận này từng là FALSE** — runner "dừng sạch" vì cả 3 email "đã có TK", trong khi thực tế email chưa bao giờ được bấm magic link; classifier nhầm màn magic-link verify → `registered_otp`.
- **Trước khi chấp nhận "dừng sạch"**: kiểm tra log `[07]` có đi qua `detected: OTP/verify screen → email DA CO tai khoan` không; nếu có → verify dump/screenshot màn lúc đó (màn magic-link verify khác màn OTP login — xem 5a). Tracking "da co TikTok" chỉ đáng tin khi classify không gộp nhầm 2 ngữ cảnh.
