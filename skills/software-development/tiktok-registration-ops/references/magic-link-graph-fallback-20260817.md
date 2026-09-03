# Magic-link Graph fallback (TikTok OTP→link auto-switch) — 2026-08-17

## Trigger
TikTok **tự đổi OTP→magic-link** khi gửi mã thất bại nhiều lần (máy 75, email
`GayeGaebel4667@hotmail.com`). Màn "Kiểm tra hộp thư của bạn" / "Bạn có thể đăng
ký bằng liên kết..." — **KHÔNG có field nhập mã**. Graph API chỉ đọc được URL,
KHÔNG bấm được link → mở bằng adb intent.

## Quyết định (user): build magic-link như fallback luôn (không chỉ hotfix máy 75)

## Implemented (commits `5633848` Tiktok_Reg)

### hotmail_provider.py
- `read_tiktok_magic_link_from_graph_token(device, email, *, token, client_id, token_file, client_id_file, stt, artifact_dir, timeout)` — giống `read_tiktok_otp_from_graph_token` nhưng trả URL magic-link, loop 8s tới deadline.
- `_graph_newest_magic_url(email, token, client_id)` — đọc 10 mail mới nhất qua Graph (`$select=subject,body,receivedDateTime,from`, `$orderby=receivedDateTime desc`).

### social_reg_v1.py
- Nhánh `prefer_magic_link` trong `handle_tiktok_email_otp` ([7c]): **thử Graph URL TRƯỚC** Outlook-app reader:
  1. `read_tiktok_magic_link_from_graph_token(..., timeout=60)` → URL
  2. `_open_magic_link_url(device_id, url)` = `am start -a android.intent.action.VIEW -d <url>`
  3. Verify TikTok rời màn magic-link → `return "MAGIC_LINK"`
  4. Không qua → fallback nhánh cũ: tap "Gửi lại email" → `read_tiktok_magic_link_from_outlook_app`

## PITFALL CRITICAL — verify "rời màn magic-link" bị FALSE POSITIVE (máy 75, cuối ngày)
Vòng verify đầu tiên: `if not any("kiem tra hop thu"/"gui lai email"/...)` → tưởng
TikTok đã rời màn magic-link → OK. **SAI**: khi `am start VIEW` mở Chrome, Chrome
chiếm foreground → dump UI không còn marker magic-link → script kết luận "đã rời"
trong khi TikTok vẫn ở màn "Kiểm tra hộp thư" (quay lại TikTok là vẫn nguyên).
→ Verify PHẢI: (a) TikTok lại foreground (APP_PACKAGE trong dump) **VÀ** (b)
không còn marker magic-link **VÀ** (c) chờ thêm vài giây sau khi quay lại TikTok.
Nếu vẫn màn "Kiểm tra hộp thư" sau khi mở URL trong Chrome → link cần mở trong
đúng context (Outlook app đã đăng nhập mail, không phải Chrome) — chỗ này chưa
giải quyết xong, user đang hướng dẫn tiếp tại thời điểm session kết thúc.

## ✅ GIẢI PHÁP CUỐI (verify live 2026-08-17 ~18:06, máy 75): ATX click nút "Xác minh email"
Chrome/`am start VIEW` + ResolverActivity chọn TikTok = dead end (link hết hạn,
hoặc mở nhưng TikTok không đánh dấu verified → vẫn popup login). Cách THẬT SỰ
chạy:
1. Outlook app đã đăng nhập mail target → mở mail TikTok ("Hoàn tất đăng ký bằng
   cách xác minh email của bạn") → nút đỏ **"Xác minh email"** (resource-id=`link`,
   class=`android.view.View`, clickable=true — bounds ~(97,1565)-(982,1697)).
2. **`adb shell input tap` KHÔNG ăn nút này** (Outlook WebView intercept) —
   phải click qua **ATX JSON-RPC** (atx-agent port 7912, method `click`, session
   `/session/<pid>:com.github.uiautomator/jsonrpc/0`). `_atx_click()` +
   `_atx_find_click()` đã thêm vào social_reg_v1.py (commit `7ef6685`).
3. ATX click → `result:true` → TikTok mở `SignUpOrLoginActivity` → qua được.

### PITFALL: ATX click mở app nhưng CHƯA chắc verified
Sau ATX click, TikTok mở nhưng nếu link đã hết hạn (~20 phút hiệu lực, mail ghi
"Liên kết có hiệu lực trong 20 phút") → vẫn màn "Tạo tài khoản" nhập email / hoặc
popup login "Số điện thoại". Chẩn đoán: login thành công phải thấy **main feed có
tab Hồ sơ + login success UI proof** — màn popup login = chưa verified.
→ User quyết định: link hết hạn thì **chạy lại reg TỪ ĐẦU** lấy mail mới (không
resume) — mail cũ chứa link chết.

## Màn login popup vs email form vs terms_consent (phân biệt — user 2026-08-17 tối)
Sau khi tap "Tiếp tục với email" hoặc link hết hạn, script dễ nhầm 3 màn:
| Màn | Marker chuẩn | Xử lý |
|---|---|---|
| **login popup** (bottom sheet: "Số điện thoại" + "Tiếp tục với email" + "Tạo tài khoản") | `so dien thoai`, `tiep tuc voi email`, `continue with email` | tap "Tiếp tục với email" |
| **email form** ("Email hoặc TikTok ID" + "Đăng nhập") | `email hoac tiktok id`, `email or tiktok id` | gõ email + tap Đăng nhập (handler ĐÃ CÓ từ trước — đừng tự thêm nhánh trùng!) |
| **terms_consent** (đồng ý điều khoản SAU khi đăng ký) | `dieu khoan dich vu` + `bang viec tiep tuc` | PENDING chờ user duyệt (có chủ đích) |

**PITFALL đã dính:** login popup có footer "Điều khoản Dịch vụ" → `_post_auth_ui_state`
match terms_consent → PENDING vô lý. Fix: state `login_popup` check TRƯỚC
terms_consent (commit `baa4173`). **ĐỪNG tự thêm handler `email_login_form`** —
script đã có flow nhập email từ trước (dòng ~2615 `email_form_markers`); tự thêm
nhánh trùng = "chế phá" user phạt. Mọi tự-sửa giữa live run = VI PHẠM STOP GATE.

## PITFALL QuickNote modal: marker `đ` có dấu — KHÔNG đổi thành `d`
Canonical `_outlook_app_quick_note_visible` (Hotmail/flows/hotmail_login.py)
nhận diện privacy notice "Ghi chú nhanh về tài khoản Microsoft" (modal có nút OK,
swipe xuống rồi bấm OK mới qua — user-confirmed 16/08). Marker privacy bullets
ghi `"ngay đay"`/`"hang đau"`/`"đang nam"` — **`đ` (U+0111) LUÔN GIỮ `đ` sau
normalize NFD** (normalize chỉ strip dấu trên chữ cái có dấu, `đ` là ký tự riêng).
Agent từng đổi `đ→d` (commit `5bd7d4a`) vì tưởng NFD strip được → **REGRESS modal
kẹt nút OK vô hạn** — phải revert. Rule (đã vào taadaa-farm-ops-rules §4.9):
marker tiếng Việt có `đ` giữ nguyên; nghi ngờ suy luận ngược với note đã verify
live → hỏi user, không sửa code theo suy luận giấy.

## PITFALL: Outlook reader `read_tiktok_magic_link_from_outlook_app` TREO VÔ HẠN
Canonical reader mở Outlook + tìm mail → nếu dính modal/phải dismiss (feedback
popup "KHÔNG, CẢM ƠN" / QuickNote / chưa vào Inbox) → **blocking treo 1.5h không
thoát** (máy 75 kẹt 13:22→15:00). Helper `_read_magic_link_with_inbox_recovery`
đảo thứ tự: **tap nút magic link TRƯỚC** (ATX find "Xác minh email"), reader
canonical chỉ gọi CUỐI cùng. Dismiss popup feedback "KHÔNG, CẢM ƠN" trước khi
tìm mail TikTok. Rule chung: script treo ≥2-3 phút = LỖI → kill + ảnh + báo user.

## Extract URL — 2 trap đã dính (máy 75)
1. **URL nằm trong href HTML, không phải body text**: mail có nút "Xác minh email"
   → `_strip_html` bỏ thẻ `<a>` → regex `https?://` trên body text KHÔNG ra URL.
   Fix: `re.search(r'href="(https?://[^"]*email_verification[^"]*)"', body_raw)` rồi
   `replace("&amp;", "&")`. Fallback URL https đầu tiên.
2. **Subject không chứa "tiktok" + marker không dấu không match**: subject thật
   "Hoàn tất đăng ký bằng cách xác minh email của bạn" — KHÔNG có "tiktok", và
   marker "xac minh email" (không dấu) KHÔNG match "xác minh email" (có dấu).
   Fix: marker tiếng Việt CÓ DẤU: `("hoàn tất đăng ký", "xác minh email", "kiểm
   tra hộp thư", "hoàn tất quy trình đăng ký", "xác nhận email của bạn")`.
   Marker link: `("magic", "liên kết", "lien ket", "link", "đăng ký", "dang ky",
   "kiểm tra hộp thư", "kiem tra hop thu", "xác minh email của bạn", "nhấp vào liên kết")`.

## URL thật (định dạng deeplink)
```
https://www.tiktok.com/ucenter_web/deeplink/email_verification?SHORTCUT_NEED_LOGIN=SHORTCUT_NEED_LOGIN_NO&aid=1180&code=<uuid>&email=<urlencoded>&language=vi&locale=vi-VN&type=16
```

## TypeError đã fix dọc đường
`read_tiktok_magic_link_from_outlook_app()` KHÔNG nhận `password` kwarg — gọi
`password=password` → `TypeError: unexpected keyword argument` → script fail khi
vào nhánh magic-link. Bỏ kwarg.

## Validate nhanh (PC-side, không cần máy)
```bash
cd /d/Taadaa/Tiktok_Reg && env -u PYTHONPATH D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -c "
import sys; sys.path.insert(0,'.')
from hotmail_provider import read_tiktok_magic_link_from_graph_token
print(read_tiktok_magic_link_from_graph_token('x','<email>', timeout=30)[:150] or None)"
```
Debug mail: `HOTMAIL_GRAPH_DEBUG=1` + gọi `resolve_graph_credentials` →
`exchange_refresh_token` → `_http_json(_GRAPH_MSGS_URL ...)` → in subject/hrefs.