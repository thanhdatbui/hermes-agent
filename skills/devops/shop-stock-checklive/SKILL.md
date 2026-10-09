---
name: shop-stock-checklive
description: Check-live (kiểm tra live) automation cho kho tài khoản trên shop SHOPCLONE7 (doravo.net) — nguồn TikTok/IG/Gmail/Hotmail/X, dọn product_stock→product_die có backup, VPS direct TikTok check, GH Actions artifact flow, web tools clonefbig/khommo247. Use when building/running/debugging check-live cron hoặc 'check live/dọn kho' cho shop acc.
---

# Check-live tự động kho tài khoản (SHOPCLONE7 / doravo.net)

## Trigger
- User nhờ: "check live", "kiểm tra live", "dọn kho", "chạy check hàng ngày" cho shop acc.
- Hàng up tay: `supplier_id = 0` — kho local bảng `product_stock`; acc die chuyển `product_die`.

## Workflow chuẩn (chạy production 2026-08-20)
1. **Xác định SP đích**: query DB qua SSH: `SELECT id,name,cost,price,status FROM products WHERE supplier_id=0` (SP up tay: 40 TikTok, 57 IG 2FA, 38/39/60/61...).
2. **Lấy stock**: JOIN `product_stock` với `products` theo `product_code = code`. Cột `uid` = username/email để check; `account` = chuỗi đầy đủ (giữ nguyên khi chuyển die).
3. **Backup TRƯỚC khi xóa**: `mkdir -p /var/www/shopclone7/backups/<ten>/<ts>` + dump TSV các bản ghi sẽ xóa (đã có backup pre-tt-clean-die/product_die).
4. **Check live theo nguồn** (ma trận dưới).
5. **Dọn DIE**: INSERT `product_die` (product_code, seller, uid, account, create_gettime, type) rồi DELETE `product_stock` — chunk 200, transaction. TRƯỚC khi xóa hàng loạt: verify mẫu DIE bằng nguồn độc lập (retry cao hơn / browser) — tránh dọn nhầm acc live.
6. **Báo cáo**: LIVE / DIE đã dọn / UNKNOWN còn lại.

## Nguồn check live — ma trận quyết định (cập nhật 2026-08-20)
| Nguồn | Nền tảng | Kết quả thực tế | Ghi chú |
|---|---|---|---|
| **VPS direct tiktok.com** (JSON rehydration) | TikTok | ✅ ~98% phân loại; UNKNOWN 377→9 với retry 4→8→12 | Không login, không web 3 — ƯU TIÊN |
| GitHub Actions (`thanhdatbui/tiktok_check_live`) | TikTok | ⚠️ 77% UNKNOWN (runner IP datacenter bị WAF) | Chỉ dùng khi cần; có fix 401 artifact |
| clonefbig.com/checklive (Playwright headful) | Instagram | ✅ qua CF Turnstile tự tick (IP dân cư) | `#inputArea` + `startCheck()` |
- **checkmail.live** (Playwright / Chrome CDP) | Gmail | ✅ Siêu tốc (~1s/batch), nhận diện chính xác Live vs Die | Cần đăng nhập session trên web, gọi `CheckEmail()`. BẮT BUỘC dùng canonical runner `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py` (tự động login, cấp session, submit batch & trích xuất kết quả). TUYỆT ĐỐI KHÔNG tự viết script probe chay hay dùng Playwright không session vì trang bắt buộc có `api_key` mới chạy. Tránh chạy 2 script cùng lúc tranh chấp `checkmail_proxy_data` (gây crash decrypt key).
| On-device `automation_core.google_health` | Gmail | ⚠️ CẤM DÙNG LÀM PRIMARY CHECK: Chỉ bắt được popup CAPTCHA/Relogin trên UI; tài khoản bị khóa/disable ngầm backend vẫn trả `target_account_not_verified` (ngộ nhận LIVE). BẮT BUỘC dùng checkmail.live để check live Gmail. | Chạy trực tiếp trên thiết bị Android farm |

## checkmail.live — Cách tương tác chuẩn xác & Vượt Cloudflare Turnstile (Cập nhật 2026-09-04)

Trang dùng **CodeMirror** editor thay vì plain `<textarea>` và **bắt buộc phải có session đăng nhập hợp lệ** (sinh `API Key` vào `document.getElementById('api-key')`):

### 1. Cơ chế xác thực & Vượt Cloudflare Turnstile qua Farm Mobile Proxy:
- Nếu chưa login: Bấm Check sẽ bị chặn bởi popup alert `You are not logged in`.
- Nếu đăng ký/đăng nhập nhiều lần trên cùng IP: Trang redirect sang `/pay/` báo `Multiple accounts detected. Your account has been banned!`.
- **Giải pháp:** Sử dụng Playwright persistent context kèm proxy mobile Farm (`http://test.taadaa.click:5101`, auth `mobi1:TaadaaMobi#2026!`) và cờ `--disable-blink-features=AutomationControlled` để Cloudflare Turnstile tự động giải sau 1-3s.
- **Quy chuẩn tài khoản:** Username bắt buộc chỉ gồm chữ và số `[a-zA-Z0-9]+` (CẤM dấu gạch dưới `_` hoặc ký tự đặc biệt), độ dài 5-12 ký tự (VD: `kibe8961`).
- **Lưu ý Turnstile DOM:** Trên `login.php`, Turnstile widget chỉ render vào `#a-form` khi click nút chuyển `.switch-btn` (truy cập thẳng `?action=signup` sẽ thiếu captcha). Đợi token `cf-turnstile-response` có giá trị rồi gọi `form.submit()` kèm input ẩn `name="signUp"` hoặc `name="signIn"`.
- **Phân loại Phone Checkpoint & Kỷ luật Bảo tồn Tài sản:** Khi một tài khoản Gmail bị Google yêu cầu nhập số điện thoại (`challenge/iap` / Phone Checkpoint), trên `checkmail.live` sẽ được phân loại chuẩn xác là **DIE** (vì bot automation không thể tự login sử dụng). Theo Invariant Farm: **`CẤM xóa Gmail DIE`** (mọi nick là tài sản). Chỉ đánh dấu trạng thái DIE / chuyển sang sheet lưu trữ `Gmail_DIE_Archive` hoặc cô lập khỏi active pool để tránh nghẽn luồng; tuyệt đối KHÔNG xóa vĩnh viễn bản ghi tài khoản khỏi Excel/DB master.

### 2. Code mẫu check batch tự động hoàn chỉnh:
```python
from playwright.sync_api import sync_playwright
import time, re

CHROME_EXEC = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"
USER_DATA = r"D:\Taadaa\GPM auto\checkmail_proxy_data"
PROXY = {"server": "http://test.taadaa.click:5101", "username": "mobi1", "password": "TaadaaMobi#2026!"}

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA,
        executable_path=CHROME_EXEC,
        headless=False,
        proxy=PROXY,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://checkmail.live/", timeout=30000)
    time.sleep(2)
    
    # 1. Tự động Login nếu chưa có session / API key
    api_key = page.evaluate("() => document.getElementById('api-key') ? document.getElementById('api-key').value : null")
    if not api_key:
        page.goto("https://checkmail.live/login.php", timeout=30000)
        page.locator("#switch-c2 .switch-btn").click() # Chuyển form Sign Up để render Turnstile
        time.sleep(2)
        username = f"kibe{int(time.time()) % 10000}"
        page.locator('#a-form input[name="fullName"]').fill("Kibe Farm")
        page.locator('#a-form input[name="userName"]').fill(username)
        page.locator('#a-form input[name="userPwd"]').fill("TaadaaKibe2026")
        page.locator('#a-form input[name="confirmPwd"]').fill("TaadaaKibe2026")
        for _ in range(20):
            t = page.evaluate("() => document.querySelector('#a-form input[name=\"cf-turnstile-response\"]')?.value || ''")
            if t: break
            time.sleep(1)
        page.evaluate('() => { const f=document.getElementById("a-form"); const i=document.createElement("input"); i.type="hidden"; i.name="signUp"; i.value="1"; f.appendChild(i); f.submit(); }')
        time.sleep(4)
        
        # Sign in
        page.goto("https://checkmail.live/login.php", timeout=30000)
        page.locator('#b-form input[name="userName"]').fill(username)
        page.locator('#b-form input[name="userPwd"]').fill("TaadaaKibe2026")
        for _ in range(20):
            t = page.evaluate("() => document.querySelector('#b-form input[name=\"cf-turnstile-response\"]')?.value || ''")
            if t: break
            time.sleep(1)
        page.evaluate('() => { const f=document.getElementById("b-form"); const i=document.createElement("input"); i.type="hidden"; i.name="signIn"; i.value="1"; f.appendChild(i); f.submit(); }')
        time.sleep(4)
        page.goto("https://checkmail.live/", timeout=30000)

    # 2. Gửi batch emails (75 emails/lần)
    payload = "\n".join(chunk_emails)
    page.evaluate('''(pl) => {
        if (window.editor) window.editor.setValue(pl);
        const btn = document.getElementById("btn-check");
        if (btn) btn.click();
    }''', payload)
    
    # 3. Poll kết quả qua liveResultEditor
    while True:
        time.sleep(1.5)
        res = page.evaluate('''() => ({
            live: window.liveResultEditor ? window.liveResultEditor.getValue() : "",
            total: jQuery("#total-count").text(),
            btn: jQuery("#btn-check").text().trim()
        })''')
        lines = [l.strip() for l in res["live"].split("\n") if l.strip()]
        if len(lines) >= len(chunk_emails) or (len(lines) > 0 and "Check" in res["btn"]):
            break
            
    # 4. Parse [Live] vs [die]
    for line in res["live"].split("\n"):
        m = re.search(r"\[([^\]]+)\]\s*([a-zA-Z0-9._%+-]+@gmail\.com)", line, re.I)
        if m:
            st, em = m.group(1).lower(), m.group(2).lower()
            if "live" in st: live_list.append(em)
            else: die_list.append(em)
```

**Pitfall:** Đừng nhúng newline (`\n`) trực tiếp bên trong JS string template khi dùng `page.evaluate("""...""")` — Playwright sẽ báo `SyntaxError: Invalid or unexpected token`. Luôn truyền payload qua argument thứ 2 của `evaluate(js_code, arg)`.

## Pitfalls (đắt tiền nhất)
- **TikTok SlardarWAF vs DIE/NOT_FOUND ngộ nhận**: Khi cào web profile TikTok (`https://www.tiktok.com/@username`) hoặc check live, nếu request bị rate-limit, TikTok trả về HTML challenge chứa chuỗi `SlardarWAF` và KHÔNG chứa thẻ `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">`. Parser nếu chỉ fallback về `NOT_FOUND` khi thiếu script tag sẽ đánh đồng nick LIVE bị WAF chặn thành nick DIE/NOT_FOUND. Phân biệt: chỉ gán `NOT_FOUND` khi trích xuất được JSON với `statusCode == 10221` hoặc HTTP 404 thật; khi gặp `SlardarWAF` hoặc timeout, phải xoay proxy (qua MobiProxy 32 ports `http://TaadaaMobi%232026%21:TaadaaMobi%232026%21@192.168.110.2:20001..20032`) và retry tối đa 2 lần. Cạn retry thì gán `BLOCKED`/`ERROR`, tuyệt đối không gán `NOT_FOUND`/`DIE` (xem `references/tiktok-profile-scraping-waf-proxy-pool.md`).
- **checkmail.live dùng CodeMirror không phải textarea thuần:** `page.fill('#input-mail')` hoặc `page.evaluate('... \n ... ')` inline đều fail. Xem section "Cách tương tác đúng qua CDP" ở trên.
- **GH Actions runner = IP datacenter → TikTok WAF chặn ~77%**; đừng kết luận acc die từ kết quả đó. Chuyển VPS direct.
- **GH artifact download 401**: API trả 302 sang signed URL và DROP Authorization → urllib tự re-send header → 401. Fix: redirect handler strip auth (code trong references/checklive-sources.md).
- **Camoufox proxy**: bắt buộc dict `{"server": "...", "username": ..., "password": ...}`; nhét creds vào server URL → `NS_ERROR_PROXY_CONNECTION_REFUSED` dù curl vẫn OK.
- **Camoufox headless bị CF chặn (Just a moment), headful qua được** — khommo247, kể cả trên VPS qua Xvfb.
- **khommo247 nút "Để sau" (modal .tool-login-gate) chỉ đóng UI — backend KHÔNG chạy check** (kết quả rỗng). Phải login thật: `/dang-nhap?return=...`, fields `loginEmail` + `loginPass`.
- **IP quyết định CF, không phải browser**: IP dân cư ✅ / datacenter VPS ❌ / proxy mobile farm ❌ (egress bị flag proxy). Không có browser nào cứu IP bị flag.
- **Mobile proxy pass chứa `#`** → URL-encode `%23` khi nhét vào URL. Pass login panel (`n0spam@@`) KHÁC pass proxy client (`TaadaaMobi#2026!` trong PROXYgandienthoai.xlsx) — đừng nhầm.
- **Cron GH Actions check 487 acc mất ~35 phút** → poll timeout ≥60 phút mới đủ.
- **Cookies DB của Chrome profile đang chạy bị lock** — không copy được; dùng CDP thay vì đọc file.
- **Isolate lỗi từng SP trong batch checklive**: Trong runner checklive tổng hợp nhiều SP (`daily_manual_stock_checklive.py`), bắt buộc bọc `try/except` độc lập cho từng SP. Lỗi timeout/cookie của một bên (ví dụ khommo247 của TikTok) tuyệt đối không được làm crash toàn bộ tiến trình khiến các SP khác (IG qua clonefbig, kiểm đếm stock SP tĩnh) bị hủy và không cập nhật/gửi báo cáo. Báo cáo Telegram phải phản ánh đúng các SP đã check thành công và đánh dấu fail riêng cho SP gặp sự cố mạng/cookie.
- **Quy tắc Silent Watchdog khi không có biến động tồn kho**: Trong `daily_manual_stock_checklive.py`, khi tất cả sản phẩm up tay đều hết hàng từ trước (`stock == 0` và `prev_stock == 0` và `sold_yesterday == 0`), script im lặng hoàn toàn (`return 0`), tuyệt đối KHÔNG gửi tin nhắn báo lặp / thông báo hết hàng về Telegram bot Doravo. Bỏ qua nghĩa là không đăng tin về bot. CHỈ gửi tin về bot khi có biến động thực tế (có sản phẩm còn tồn kho `> 0`, sản phẩm vừa chuyển sang hết hàng trong ngày, hoặc có đơn hàng mới phát sinh).
- **Nguyên tắc im lặng khi kho up tay không biến động (Silent Watchdog Pattern)**: Trong script báo cáo kho up tay hàng ngày (`daily_manual_stock_checklive.py`), "bỏ qua không báo lặp" nghĩa là **im lặng hoàn toàn, không gửi tin về bot** (`return 0` khi `report_lines` rỗng). Tuyệt đối không gửi tin nhắn rỗng kiểu "ℹ️ Các sản phẩm up tay hiện đều đang hết hàng từ các ngày trước...". CHỈ gửi báo cáo qua Telegram bot khi có biến động thực tế (có sản phẩm còn hàng > 0, vừa hết hàng hôm nay, phát sinh đơn bán hôm qua hoặc có die mới dọn).
- **Windows OpenSSH Bad Permissions (`~/.ssh/config` dính SID mồ côi)**: Khi cronjob check-live kết nối SSH đọc VPS Doravo gặp lỗi `VPS SQL error: Bad permissions. Try removing permissions for user: UNKNOWN\UNKNOWN (S-1-5-21-...) on file C:/Users/<User>/.ssh/config` hoặc `Bad owner or permissions`: Windows OpenSSH chặn truy cập vì ACL chứa SID rác. Sửa bằng cách ngắt kế thừa ACL trên thư mục `~/.ssh` và reset quyền qua PowerShell (xem chi tiết tại skill `shopclone7-site-ops` mục "SSH access — pitfalls").
- **Lệch tồn kho so với 'đã bán hôm qua' (Stock delta vs sold_yesterday divergence)**: Khi báo cáo ghi giảm tồn `delta` nhiều hơn `sold_yesterday`:
  1. Kiểm tra thời điểm lưu state thành công gần nhất (`checklive_state.json` hoặc log cron `output/1cb63d617582/*.md`). Nếu cron ngày hôm trước bị crash/bỏ lỡ, mốc so sánh `prev_stock` là từ 2+ ngày trước.
  2. `sold_yesterday` trong SQL chỉ quét đúng 1 ngày lịch dương (`CURDATE() - 1`). Muốn đối chiếu chính xác, query `product_order` từ mốc thời gian lưu state cũ đến hiện tại và cộng với số lượng `product_die` dọn trong khoảng đó: `delta = SUM(amount_period) + SUM(die_cleaned)`.

- **CloneFBIG API mua Hotmail/Outlook Graph API (ID 3470) & Trạng thái Token (Cập nhật 2026-09-05)**:
  - *Lịch sử (2026-08-29)*: Từng bị lỗi trường DB bên shop cắt cụt refresh token còn ~101 ký tự.
  - *Hiện tại (Đã fix 2026-09-05)*: API `/ajaxs/client/product.php` (hoặc `/api/buy_product`) với `action=buyProduct` đã trả về chuỗi Token đầy đủ nguyên vẹn (480–525 ký tự chuẩn Microsoft MSA Artifacts).
  - Định dạng data trả về: `Email|Password|Refresh Token|Client ID|Recovery Email`.
  - Tool mua tự động chuẩn: `D:\Taadaa\tools\buy_hotmail.py` (đồng bộ sang `AI-Tools` và `Hotmail`) hiện đặt CloneFBIG làm default provider, tự động duyệt `categories -> products` qua `/api/products.php` để lấy tồn kho, trích xuất `recovery_email` và nạp vào cột 5 của `gmail_clean_v2.xlsx`. Có cờ chuyển provider: `--provider clonefbig` hoặc `--provider boxtaikhoan` (ID 129).

- **Đánh giá nguồn Mail dongvanfb.net (Cập nhật 2026-09-21)**:
  - *Kiến trúc & API*: Frontend Nuxt/Vue, API public `https://api.dongvanfb.net/api/products_lists` (dùng để kiểm tra real-time danh mục, tồn kho và giá mà không cần API key). Mua hàng qua API `GET https://api.dongvanfb.net/user/buy?apikey=<KEY>&account_type=<ID>&quality=<QTY>&type=full`.
  - *Định dạng token*: Trả về `email|password|refresh_token|client_id` (hỗ trợ đọc qua Microsoft Graph API / OAuth2).
  - *Phân loại hàng*: Chỉ có 2 nhóm chính: "Mail Chuyên để Very FaceBook" (ID 5/59/6/60) và "Mail PVA" (ID 57/58 kèm mail khôi phục).
  - *Cảnh báo TikTok*: **TUYỆT ĐỐI KHÔNG CÓ** sản phẩm cam kết "Chưa qua TikTok" (Zin TikTok). Tệp mail trên sàn này chuyên dụng cho Facebook/Instagram/Twitter, không bao zin TikTok nên có rủi ro cao đã bị cày reg TikTok trước đó (dính lỗi "Tài khoản đã tồn tại").

## Setup DB + cron
- `ssh -i ~/.ssh/doravo_deploy root@152.42.187.200`; đọc `/root/.shopclone7_db_credentials` (DB_HOST/DB_USER/DB_PASSWORD/DB_NAME); `mysql -h$HOST -u$USER -p$PWD $DB -N -e "..."` qua SSH.
- Hermes cron daily: script `C:/Users/Kibe/AppData/Local/hermes/scripts/daily_manual_stock_checklive.py` (V2: TikTok VPS-direct 2 vòng retry 8→12 + IG clonefbig), `0 7 * * *`.
- Hermes browser CDP: Chrome profile `$HERMES_HOME/browser_profile` chạy `--remote-debugging-port=9222`; `playwright connect_over_cdp("http://127.0.0.1:9222")` chia sẻ cookies/cf_clearance — kết nối được kể cả khi session khác đang giữ profile.

## References
- `references/tiktok-profile-scraping-waf-proxy-pool.md` — TikTok profile scraping WAF challenge vs NOT_FOUND, 32-port MobiProxy smart retry, TikTok 64-bit Snowflake timestamp decoding (ngày tạo acc/video qua `id >> 32`), và yt-dlp native challenge bypass.
- `references/checkmail-live-farm-operations-guide-20260912.md` — Checkmail.live integration cho Gmail farm reg & bài học on-device health false-positive (2026-09-12).
- `references/checklive-sources.md` — từng nguồn chi tiết + code (TikTok direct VPS, GH Actions + fix 401, clonefbig, khommo247 selectors/gate).
- `references/gmail-checkmail-live-vs-on-device-health-trap.md` — Bẫy ngộ nhận Live từ on-device health check khi Gmail bị khóa ngầm; bắt buộc dùng checkmail.live qua mobile proxy.
- `references/checklive-runner-failure-isolation.md` — Quy tắc bọc try/except độc lập cho từng SP trong runner tổng hợp, chống crash lan sang các bên còn lại khi 1 site timeout (2026-08-28).
- `references/silent-watchdog-pattern-shop-stock.md` — Quy chuẩn Silent Watchdog cho kho hàng (im lặng hoàn toàn khi không biến động) & kỷ luật cấm lưu quy tắc vào Memory gây nặng bot.
- `references/mobiproxy-panel-api.md` — panel MobiProxy (test.taadaa.click): login riêng, API proxy_check/getlist/getip, api.php actions.
- `references/sumistore-reseller-api-integration.md` — Kiến trúc đấu nối API kho hàng sumistore.me (HMAC-SHA256, Idempotency, async queue và Telegram bot API ID).