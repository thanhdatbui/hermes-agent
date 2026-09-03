# Outlook-app magic-link provider: Focused Inbox + newest-row fallback (máy 38, 2026-08-15)

Session thực chiến chữa run 38 (email `florencenaomierayven6@hotmail.com`) — provider
`read_tiktok_magic_link_from_outlook_app` (Hotmail repo, `flows/hotmail_login.py`).
Mục đích: ghi lại đúng các lỗi gặp phải khi provider chạy lần đầu trên máy thật, để
lần sau không lặp lại vòng sửa-mock-test.

## Chuỗi fail thực tế (theo thứ tự)

| Lần | Lỗi | Root cause |
|---|---|---|
| resume r1 | `OUTLOOK_APP_INBOX_LOST_DURING_MAGIC_LINK_READ` | `_outlook_app_account_present` mở drawer; BACK để đóng nhưng **BACK thoát app** (inbox là root activity) khi drawer đã tự đóng → inbox lost |
| resume r2 | `MAGIC_LINK_NOT_VERIFIED:no_newest_tiktok_row` (timeout 180s) | (a) mail TikTok nằm trong tab "Khác" của **Focused Inbox** — provider quét tab "Ưu tiên"; (b) row không có time token trong accessibility tree |
| full f2 | `[02_profile] Khong vao duoc tab Ho so/Profile` | máy đang kẹt màn magic-link reg dở (không có tab Profile) — full flow không hợp, phải `--resume` |
| full f3 | `OUTLOOK_APP_INBOX_LOST` (~36s) | provider tap row TikTok (fallback chọn mail CŨ 22 Th7 "776628 là mã TikTok") → không phải magic-link → BACK → thoát app |

## Evidence quan trọng

- Màn magic-link TikTok (XML fail_02 / debug_otp): rid `dtn` text "Kiểm tra hộp thư của bạn",
  rid `dtl` text "Bạn có thể đăng nhập bằng liên kết được gửi đến <email>", rid `tpf`
  clickable "Gửi lại email sau 20 giây". **Không có EditText OTP**.
- Màn magic-link **không có tab Profile** → tap (972,1857) vô tác dụng.
- Outlook app: email TikTok từ tháng trước "776628 là mã TikTok của bạn" (22 Th7) —
  OTP + nút "Xác minh email" nhưng KHÔNG có cụm magic-link ("liên kết được gửi đến"/"đăng ký bằng liên kết").
- Vision 10:50 inbox: tab "Ưu tiên" (Focused) active, group "Email khác" chứa 7 mail TikTok collapsed.
- uiautomator: `uiautomator dump` → "Killed" liên tục (OOM thiết bị cũ, kể cả `--compressed`,
  kể cả sau force-stop app khác). Screenshot + vision + `dumpsys activity top` là phương án thay thế.

## Fix đã merge (Hotmail `flows/hotmail_login.py`)

1. **Đóng drawer an toàn**: chỉ `keyevent 4` khi `_outlook_app_drawer_open(after_identity)`;
   sau đó re-capture + re-verify `outlook_app_inbox_visible`; gán `xml = after_identity`.
2. **`_outlook_app_newest_tiktok_row` fallback**: time-bearing row ưu tiên (regex mở rộng:
   `\d{1,2}:\d{2}`, `\d{1,2} giờ`, `hôm nay/hôm qua`, `thứ N`, `thg`, day name); nếu không có
   → row TikTok clickable đầu tiên theo DOM order (Outlook newest-first). Vẫn skip URL chrome + y<240.
3. **`_outlook_app_focused_tab_coord(xml, *labels)`**: tìm node clickable label khớp chính xác
   ("khac"/"other") trong band y∈[72,340). Gọi trong vòng lặp khi không thấy row, đúng 1 lần
   (`other_tab_tried` flag), tap rồi continue.
4. Test `tests/test_outlook_app_magic_link.py`: `_outlook_app_focused_tab_coord`,
   fallback row không time, ưu tiên time row, entrypoint drawer-close flow.

## Pitfalls mock/test (đã dính)

- **Mock `_outlook_app_drawer_open` return_value=True làm `outlook_app_inbox_visible` luôn False**
  (`_outlook_app_active_folder` gọi drawer_open → True → active folder None → inbox false) → test
  vào nhầm archive branch. Phải dùng `side_effect=[False, False, True, False, ...]` theo đúng
  thứ tự: lần check inbox đầu (đóng), check sau archive (đóng), sau identity (mở) → BACK → đóng.
- Khi thêm bước (đóng drawer) vào entrypoint, mock `ui_xml` side_effect phải đủ phần tử theo
  đúng thứ tự gọi mới — thiếu → `StopIteration`/sai state.

## Trạng thái cuối session

Provider đã đi xa hơn: mở được email TikTok (mail cũ 776628) — chứng minh vòng đọc inbox +
row selection hoạt động; fail còn lại là semantic (mail cũ OTP không phải magic-link) và
BACK-thoát-app (đã fix bằng re-verify). Email florencen thực ra đã có account (login continuation),
không phải reg mới — cần phân loại lại target trước khi chạy tiếp.

## Bổ sung cuối session (11:04-11:20)

### User xác nhận: tab "Khác" là đường duy nhất thấy mail TikTok

User (ảnh màn hình farm panel 11:16): "phải bấm vào chữ khác trong hotmail mới hiện mail
tiktok. chữ ưu tiên nó bị gom vào 1 chỗ". Tab "Ưu tiên" (Focused) gom mail quen thuộc;
TikTok (sender lạ) bị xếp vào tab **"Khác"**. Vision 11:18 sau khi Outlook restart: tab "Khác"
đang chọn (nền trắng) → mail TikTok hiện rõ: "Hoàn tất đăng ký bằng cách xác minh em..." 11:01
(mail magic-link MỚI — resend từ resume3 đã thành công!), 08:57, "340208 là mã TikTok của bạn"
08:34, "828736 là mã Ti...". Mail mới 11:01 có time "11:01" → regex time match.

### Tab-switch cần fallback tọa độ cố định khi uiautomator OOM

`_outlook_app_focused_tab_coord` đòi node clickable trong XML — nhưng trên máy 38 uiautomator
hoàn toàn không dump được inbox (OOM), nên XML rỗng → coord None → không tap được tab.
Fix đã merge: `other_coord is None → (330, 165)` (band header, cạnh "Ưu tiên"). Tab "Khác"
tọa độ từ vision: ~(345, 163).

### uiautomator OOM cứng trên máy 38 — ladder B1/B2/B3 KHÔNG cứu

- `uiautomator dump` → `EXIT=137`/`Killed` liên tục, kể cả `--compressed`, kể cả sau
  force-stop Chrome + Play Store (MemFree 78MB → 455MB, vẫn fail). KHÔNG phải ATX treo —
  `pkill -f uiautomator` bị `Operation not permitted` (service `com.github.uiautomator`).
- `uiautomator dump /dev/stdout` (exec-out) cũng fail (RAW LEN 6 = "Killed") — fallback
  exec-out trong `ui_xml` không cứu.
- Cách đọc trạng thái thay thế hoạt động: `dumpsys activity activities` (mResumedActivity),
  `dumpsys window windows` (focus), `dumpsys activity top` (không expose text mail nhưng
  thấy `app:id/drawer_mail_header` = drawer mở), screenshot + `vision_analyze` (retry khi 401).
- **Chẩn đoán phân biệt**: OOM-kill uiautomator ≠ ATX treo (B1 ATX-kill không giúp; máy vẫn
  dump OK trước đó vài phút); ≠ RAM thiếu đơn thuần (giải phóng RAM không cứu — service đã hỏng).
- **Cách duy nhất còn lại: `adb reboot` máy** (reboot thiết bị, KHÔNG restart ADB server —
  không vi phạm rule; máy không worker/lock active thì an toàn). Chưa thực hiện trong session
  (cần user chốt).

### CẤM force-stop TikTok khi muốn giữ màn reg dở — NHƯNG nhánh magic-link thì OK

Sau khi monkey launch đưa app lên (không phá màn reg trong task — XML vẫn thấy "Kiểm tra
hộp thư"), **`am force-stop com.ss.android.ugc.trill` XÓA task reg** → lần mở sau về
MainActivity/Profile account cũ, màn magic-link dở mất hẳn → không còn gì để resume, phải
full lại từ đầu (rồi dính lỗi `[02_profile]` nếu máy lại kẹt magic-link). Chỉ force-stop
TikTok khi chấp nhận bỏ màn reg dở.

**NGOẠI LỆ (user chỉ rõ 2026-08-15 ~11:20):** với nhánh MAGIC-LINK thì force-stop TikTok
là ĐÚNG — "hay magic link thì cứ vào hotmail bấm k cần quan tâm... close tiktok đi giải
phóng ram rồi vào hotmail bấm là xong". Link magic-link trong mail **tự deep-link quay lại
TikTok** (mở `TransparentCodeVerificationActivity` / CommonFlowActivity), KHÔNG cần giữ màn
OTP sống. Trên máy yếu (S7 máy 38), close TikTok giải phóng 621MB RAM → đủ cho Outlook +
uiautomator dump → mở mail → bấm "Xác minh email" là xong. Chỉ nhánh NUMERIC OTP mới cần
giữ màn (enter_otp_code cần màn 6 ô). Phân biệt theo mode đã classify từ màn TikTok.

### "Gửi lại email" resend tap + bàn phím che nút

- Resume3 có tap "Gửi lại email" thành công (mail mới 11:01 về!) nhưng log r1/r2 báo
  "Không thấy: ('Gửi lại email'...)" vì **bàn phím IME mở che nút** (nút nằm dưới vùng che).
  Fix: `keyevent 4` đóng bàn phím trước (vẫn giữ màn), sleep 1s, rồi mới `find_text_tap`.
- Resend KHÔNG bắt buộc (provider tự refresh + chờ) — nhưng nếu mail magic-link chưa về,
  resend là cách ép TikTok gửi mail mới.

### `_outlook_app_magic_link_message` markers mở rộng cho mail legacy

Mail TikTok cũ "776628 là mã TikTok của bạn" (22 Th7) có "Nhấp vào liên kết này hoặc nhập
mã 776628" + nút "Xác minh email" — KHÔNG có "liên kết được gửi đến"/"đăng ký bằng liên kết".
Marker cũ quá hẹp → provider từ chối mail này dù nó có action. Đã thêm markers legacy:
"nhấp vào liên kết này", "hoặc nhập mã", "hoàn tất đăng ký", "để xác nhận email", v.v.

### Time regex mở rộng cho "22 Th7" format

"22 Th7" (22 tháng 7) không match regex cũ (`t[2-7]\b` = "T2".."T7" thứ, không phải "Th7").
Thêm: `th\d{1,2}\b`, `\d{1,2}\s*th\b`, `\d{1,2}\s*thg\b`.

### BACK từ email-detail thoát app — cần in-app back arrow

Trên Outlook app, BACK (keyevent 4) từ email-detail có thể thoát hẳn app (inbox root).
Fix đã merge: `_outlook_app_back_to_inbox` ưu tiên tap **in-app back arrow** (top-left,
y<240, desc "Quay lại"/"back") trước khi keyevent 4.

### Row TikTok = clickable CONTAINER, text nằm trong child nodes (fix 11:40)

Bằng chứng DOM thật (dump inbox tab Khác sau reboot 11:40, LEN 34399): row mail là
container clickable `bounds=[0,560][1080,805]` với `text=""` rỗng, text thật nằm ở child:
`<node text="TikTok">`, `<node text="Hoàn tất đăng ký bằng cách xác minh emai...">`,
`<node text="11:34">`. Hàm cũ `_outlook_app_newest_tiktok_row` chỉ đọc label của chính
node clickable → rỗng → `"tiktok" not in label` → None → `no_newest_tiktok_row` timeout
dù mail có trong hộp. **Fix đã merge**: gộp label node + label TẤT CẢ descendant
(`for child in node.iter("node")`) trước khi match `tiktok` + time_pattern. Test mới:
`test_newest_tiktok_row_matches_container_with_child_text` (fixture nested node container).
**Bài học chung**: trên Outlook app, mọi row-parsing phải aggregate descendant text —
time token ("11:34") và sender ("TikTok") thường nằm ở child TextViews, không ở node
clickable. Cùng pattern áp dụng cho `_outlook_app_magic_link_message` (đã dùng
`visible_flat_text` gộp toàn cây nên OK).

### `OUTLOOK_APP_ACTIVITY_NOT_RESOLVED` — `am start` race khi TikTok chiếm foreground

full4/full5 fail mới (11:35/11:48): provider vào [7c] → `open_outlook_app` chạy
`am start -a MAIN -c LAUNCHER -p com.microsoft.office.outlook` → nhưng TikTok vẫn
foreground (SignUpOrLoginActivity) → `wait_for` inbox timeout → fail → `_write_outlook_app_result`
gọi `active_outlook_app_component` → dumpsys không thấy Outlook → raise
`OUTLOOK_APP_ACTIVITY_NOT_RESOLVED`. Khác biệt: **chạy tay `am start` từ terminal/consumer
shell THÀNH CÔNG** (Outlook resumed t92) — chỉ fail khi provider gọi trong race với TikTok
đang animate sau submit email. Chẩn đoán: sau fail, `dumpsys activity activities` chỉ thấy
TaskRecord trill, không có TaskRecord outlook = `am start` không launch được hoặc bị trễ.
Hướng xử lý (chưa merge): provider nên verify `mResumedActivity` thành Outlook sau
`am start` (retry 2-3 lần) trước khi `wait_for`; hoặc consumer đưa TikTok về HOME
(`keyevent 3`) trước khi gọi provider. Ghi nhận: `OUTLOOK_APP_ACTIVITY_NOT_RESOLVED`
là signature mới khác các lỗi inbox/drawer cũ — đừng nhầm với OOM/ATX.

### Reboot chỉ cứu được ~1 pass provider — uiautomator chết lại sau khi đổi app nặng

Chuỗi reboot 11:26 / 11:40: sau mỗi `adb reboot`, dump OK (22KB/31KB, EXIT=0) — nhưng
**chỉ duy nhất 1 lần**: mở TikTok nặng (621MB RSS) + chuyển foreground qua lại rồi mở
Outlook → `uiautomator dump` lại EXIT=137 kể cả trên launcher, kể cả sau force-stop
TikTok/Chrome giải phóng RAM (MemFree 400MB). Logcat: `UiAutomationShellWrapper.connect`
fail → uncaughtException → service `com.github.uiautomator` chết (pkill bị
`Operation not permitted`). Kết luận: máy 38 chỉ đủ sức **1 lượt provider đọc inbox
sau mỗi reboot** — kế hoạch chạy phải: reboot → mở Outlook trước (mail đã về sẵn) →
provider đọc ngay trong cửa sổ ổn định, KHÔNG để flow mở TikTok nặng giữa chừng.
Đây là giới hạn thiết bị (S7, RAM 3.6GB, Android 7), không phải bug code — đừng sửa
code thêm cho pattern này.

## Bổ sung 12:05-12:19 — tap link thành công bằng pixel-scan (uiautomator chết)

Khi uiautomator chết cứng (không dump được inbox), vẫn tap được nút "Xác minh email"
trong mail Outlook bằng **tọa độ từ PIL pixel-scan** — chain đã chứng minh thành công:

### Vision scale trap (2 lần tap trật)

- `screencap` ra file 1080x1920 đúng, nhưng `vision_analyze` báo ảnh **720x1280** hoặc
  **1080x1450** (model crop status bar/navigation) → tọa độ vision phải nhân tỷ lệ
  (1080/720 = 1.5x) trước khi tap. Tap trực tiếp tọa độ vision (540,495) trật: mở
  `SubSettingsActivity` (settings) thay vì mail.
- Vision trả tọa độ KHÔNG ỔN ĐỊNH giữa 2 lần gọi cùng 1 ảnh: nút "Xác minh email"
  lần 1 báo center (360,849), lần 2 báo (360,1085) — chênh 236px. Tap mù theo vision
  rủi ro thoát app (trúng "Trả lời"/bottom bar → Outlook về launcher).

### Pixel-scan đáng tin hơn

Script PIL (chạy bằng `env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python`):
scan ảnh 1080x1920 gốc, tìm cluster pixel màu đặc trưng của nút TikTok CTA
(đỏ hồng: `r>180, g<120, b<120, r-g>80`), group theo y liền nhau, in center:
`red cluster: y=[1568,1696] x=[226,852] center=(539,1632) size=128x626`. Nút thật =
cluster lớn (128px cao, 626px rộng); cluster nhỏ (8px, toàn ngang) = dải trang trí email.
Tap (539,1632) → `mResumedActivity` = `com.ss.android.ugc.trill/...TransparentCodeVerificationActivity`
= **link magic-link ĐÃ kích hoạt thành công**.

### TransparentCodeVerificationActivity kẹt trên máy yếu

Tap link mở đúng activity verify của TikTok nhưng nó **đứng im không tự chuyển**
(BACK không đóng được; chờ 12s+ vẫn vậy) trên máy S7 yếu — verify phía client chưa
hoàn tất, account chưa được thêm (dropdown vẫn chỉ benghxmk3zu/thy.dung1828). Khi gặp:
force-stop + relaunch TikTok → nếu account mới chưa xuất hiện, có thể link đã hết hạn
(20 phút) hoặc cần full-flow lại (email có thể đã verify phía server → lần submit sau
sẽ vào thẳng bước tạo mật khẩu). Đừng kết luận "verify xong" chỉ vì activity mở.

### Quy trình tap tọa độ an toàn khi uiautomator chết

1. Mở app → tap row mail (tọa độ từ pixel-scan/vision tỷ lệ 1.5x) → verify `mResumedActivity`
   (mail mở trong CentralActivity không đổi activity — dùng pixel-scan kiểm tra có nút đỏ).
2. **Chụp ngay** → pixel-scan nút → **tap ngay** (không chụp lại giữa chừng — màn có thể đổi,
   tap tọa độ cũ trật).
3. Verify: `mResumedActivity` đổi sang TikTok = thành công; thoát về launcher = tap trật
   (trúng nút khác / bottom bar).
