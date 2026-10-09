# Muasamcong (National E-Procurement) Chrome CDP Automation & Medical Tender Research

## Context & Background
- **Target Portal**: Hệ thống mạng đấu thầu quốc gia (`https://muasamcong.mpi.gov.vn/`).
- **User Directive**: *"dùng chrome CDP ấy, sao mà lâu thế"* — User prefers using the existing running Chrome session via CDP (`127.0.0.1:9222`) rather than slow standalone headless browser launches or generic browser tools that risk WAF blocks or connection resets.
- **Domain Scope**: Medical devices & consumables procurement (Trocar, wound protectors/SILS access devices, laparoscopic powered staplers & reloads).

## Network & Connectivity Pitfalls
1. **Network Reset / SSL Handshake Timeout**:
   - `muasamcong.mpi.gov.vn` (IP `103.186.152.30` / `103.186.152.10`) frequently drops or resets direct TLS handshakes (`ERR_CONNECTION_RESET` or SSL timeout) on certain consumer ISPs.
   - **Resolution**: Route traffic through the active local WARP SOCKS5 proxy (`socks5://127.0.0.1:40000`).
   - In Chrome CDP, create an isolated browser context bound to the proxy without disrupting other tabs or modifying system network settings:
     ```python
     await cdp_call(ws_browser, 'Target.createBrowserContext', {'proxyServer': 'socks5://127.0.0.1:40000'})
     ```
     This allows instant page load (HTTP 200) without triggering IP-level blocks.

2. **reCAPTCHA v2 Bypass via CDP**:
   - The login form (`/security/auth/realms/egp/...`) contains Google reCAPTCHA v2.
   - Because the user's Chrome profile has high trust reputation, dispatching a synthetic mouse click on the checkbox:
     ```python
     await cdp_call(ws_page, 'Input.dispatchMouseEvent', {
         'type': 'mousePressed', 'x': checkbox_x, 'y': checkbox_y, 'button': 'left', 'clickCount': 1
     })
     await cdp_call(ws_page, 'Input.dispatchMouseEvent', {
         'type': 'mouseReleased', 'x': checkbox_x, 'y': checkbox_y, 'button': 'left', 'clickCount': 1
     })
     ```
     will immediately satisfy the challenge (`g-recaptcha-response` length > 2000) without displaying image grids.
   - Followed by Google Authenticator 2FA step if configured on contractor account.

## Domain Glossary & User Expectation: "Yêu cầu HSMT"
- **User Statement**: *"Yêu cầu hsmt trên mua sắm công... Stapler điện dùng pin 1 lần gần đúng theo sản phẩm của anh"*
- **Critical Semantic Distinction**:
  - `KQLCNT` (Kết quả lựa chọn nhà thầu): Chỉ là bảng tên gói, đơn vị trúng thầu, giá trúng thầu.
  - `HSMT` (Hồ sơ mời thầu) / `E-HSMT`: Là toàn bộ hồ sơ mời thầu điện tử.
  - **"Yêu cầu HSMT"**: Cụ thể là **Chương V - Bảng yêu cầu kỹ thuật & Mẫu số 02A (Phạm vi cung cấp hàng hóa)**.
  - Khi nhà thầu/đối tác hỏi *"Yêu cầu hsmt"*, họ muốn xem bảng thông số kỹ thuật chi tiết (Ký mã hiệu, Nhãn hiệu, Hãng sản xuất, Xuất xứ, Tiêu chuẩn kỹ thuật chi tiết như pin tích hợp, số hàng ghim, kích cỡ nòng Trocar...) để:
    1. So sánh đối chiếu với sản phẩm họ đang phân phối có đủ điều kiện dự thầu không.
    2. Phát hiện các "tiêu chí cài cắm" độc quyền của chủ đầu tư (chỉ định riêng cho Medtronic, J&J, hay Covidien).

## Muasamcong Excel Export Schema (`DANH_SACH_HANG_HOA (XX).xlsx`)
When downloading item-level procurement results from Muasamcong, the file contains a 25-column schema (skip row 1 header metadata):
- `Col 1`: STT
- `Col 2`: Tên thiết bị, vật tư y tế
- `Col 3`: Đơn vị tính
- `Col 4`: Khối lượng / Số lượng
- `Col 5`: Xuất xứ (quốc gia, vùng lãnh thổ)
- `Col 6`: Mã HS
- `Col 7`: Kỹ mã hiệu
- `Col 8`: Nhãn hiệu
- `Col 9`: Hãng sản xuất
- `Col 10`: Chủng loại (model)
- `Col 11`: Số lưu hành hoặc số giấy phép nhập khẩu
- `Col 12`: Năm sản xuất
- `Col 13`: Cấu hình, tính năng kỹ thuật cơ bản (chứa trích đoạn Chương V E-HSMT)
- `Col 14`: Đơn giá trúng thầu (VNĐ)
- `Col 15-16`: Mã định danh & Tên NT trúng thầu
- `Col 17`: Mã TBMT
- `Col 18-19`: Mã định danh & Tên CĐT (Bệnh viện)
- `Col 20`: Hình thức LCNT (Chào giá trực tuyến, Đấu thầu rộng rãi...)
- `Col 21`: Ngày đăng tải KQLCNT
- `Col 22-23`: Số quyết định & Ngày ban hành
- `Col 24`: Số nhà thầu tham dự
- `Col 25`: Địa điểm thực hiện

### Parsing & Categorization Rules:
1. **Powered Stapler (Máy chạy pin)**: Filter by `pin` or `powered` in `Col 2` or `Col 13`.
   - Cán máy trúng thầu: ~14.000.000 đến 21.000.000 VNĐ/cái (VD: Ethicon ECHELON FLEX Powered Plus 17.155.250 VNĐ; ECHELON 3000 21.059.325 VNĐ).
2. **Reloads / Băng ghim**: Filter by `băng ghim`, `đạn`, `ghim` or `reload`.
   - Băng ghim trúng thầu: ~3.800.000 đến 5.500.000 VNĐ/băng (VD: Covidien Tri-Staple 5.500.000 VNĐ; Ethicon GST 4.469.063 VNĐ; Panther/Waston 3.868.000 - 4.200.000 VNĐ).
3. **Trocar nội soi**: Filter by `Trocar` in `Col 2`.
   - Xuất xứ TQ/Hàn Quốc: ~450.000 đến 950.000 VNĐ/cái.
   - Xuất xứ Mỹ/Âu: ~1.450.000 đến 2.100.000 VNĐ/cái.

## Automated Daily Monitoring Architecture (Watchdog Pattern)
- Script: `muasamcong_daily_watchdog.py` (located in `%LOCALAPPDATA%\hermes\scripts\`) connecting via `cdp_eval.py` to Chrome CDP :9222.
- **Doravo Bot Telegram Integration**:
  - Token and Chat ID extracted from MariaDB `shopclone7.settings` on the VPS (`root@152.42.187.200`): `settings.telegram_token` (`doravo_stock_alert_bot`), `settings.telegram_chat_id` (`-1004418200690`).
  - Cached locally at `%LOCALAPPDATA%\hermes\doravo_bot_config.json` to eliminate recurring SSH queries during daily cron runs.
  - Sends direct POST requests to `https://api.telegram.org/bot<token>/sendMessage`, with automatic failover fallback through local WARP proxy (`socks5h://127.0.0.1:40000`).
- **Dynamic Tab Acquisition & Anti-Crash Discipline (CỰC KỲ QUAN TRỌNG)**:
  - **Pitfall**: Tuyệt đối KHÔNG hardcode Browser WebSocket GUID (`ws://127.0.0.1:9222/devtools/browser/<guid>`). Mỗi lần Chrome restart, GUID này sẽ bị hủy, khiến `cdp_call` trả về `None` và gây văng lỗi `TypeError: 'NoneType' object is not subscriptable` khi đọc `res['result']['targetId']`.
  - **Chuẩn hóa**:
    1. Kiểm tra liveness bằng `http://127.0.0.1:9222/json/version`.
    2. Quét danh sách tab bằng `http://127.0.0.1:9222/json/list` tìm tab `muasamcong.mpi.gov.vn` đang mở.
    3. Nếu chưa có tab: Mở tab mới động bằng HTTP `PUT http://127.0.0.1:9222/json/new?about:blank`, đọc `webSocketDebuggerUrl` trả về rồi dùng `Page.navigate` để tải trang.
- **Auto-heal Helper (`ensure_cdp_browser()`)**:
  - Nếu Chrome bị tắt do reboot hoặc người dùng tắt nhầm: tự động gọi `subprocess.Popen` khởi chạy lại Chrome đính kèm `--remote-debugging-port=9222` và `--user-data-dir="C:\Users\Kibe\AppData\Local\hermes\browser_profile"`, chờ tối đa 30s cho CDP online trước khi điều khiển.
- **Quy trình nghiệm thu & Chống bắn tin nhắn kép (Anti-Duplicate Alarm)**:
  - Khi sửa code watchdog và chạy thử: KHÔNG chạy lệnh test manual xong bấm ngay `cronjob(action='run')` vì sẽ bắn liên tiếp 2 tin nhắn giống nhau trong 1 phút khiến user thắc mắc ("Sao gửi làm 2 lần v").
  - Nếu cần kiểm tra cả scheduler, hãy giải thích rõ cho user hoặc pass cờ silent/dry-run cho lần test tay.
- Dual Search Flow Requirement (TBMT + YCBG):
  - Mua Sắm Công separates tenders into distinct radio search modes:
    - TBMT (Thông báo mời thầu): `input[type="radio"][value="notifyNo,bidName"]`
    - YCBG (Yêu cầu báo giá): `input[type="radio"][value="ycbg"]`
  - BẮT BUỘC phải chuyển đổi (toggle) và quét độc lập cả 2 chế độ radio cho từng từ khóa. Các bệnh viện công thường xuyên phát hành YCBG để khảo giá trước khi lập dự toán/mời thầu nhiều tuần; bỏ sót YCBG đồng nghĩa bỏ lỡ cơ hội chào giá vật tư y tế ngay từ đầu.
- Divergent Lifecycle Labels & DOM Badges (CỰC KỲ QUAN TRỌNG - BẪY PARSER):
  - TBMT (Thông báo mời thầu): Thẻ chứa `Mã TBMT : IB...`, thanh thống kê hiển thị `Chưa đóng thầu (N)` và `Đã đóng thầu (N)`.
  - YCBG (Yêu cầu báo giá): Thẻ chứa `Mã YCBG : RQ...`, trạng thái hiển thị trực tiếp trong từng thẻ là `Chưa hết hạn nhận báo giá` (đang mở) vs `Đã hết hạn nhận báo giá` (đã đóng). Thanh thống kê YCBG KHÔNG có chuỗi "Chưa đóng thầu".
  - Parser chỉ dùng regex `Chưa đóng thầu (\d+)` sẽ HOÀN TOÀN BỊ ĐIẾC trước các gói YCBG đang mở (luôn trả về 0 gói mở dù thực tế có gói mới như RQ2600056970 của BV Nguyễn Trãi). BẮT BUỘC parse riêng:
    - TBMT: bắt `Chưa đóng thầu (\d+)`
    - YCBG: đếm các block chứa `Chưa hết hạn nhận báo giá` hoặc regex `Chưa hết hạn nhận báo giá`
- Session Status & Anti-Hardcode Discipline:
  - Khi Chrome CDP duyệt ở chế độ Guest/chưa login (`localStorage.getItem("userDTO") === null`), TUYỆT ĐỐI KHÔNG hardcode mã nhà thầu (`vn0402332245`) vào nội dung tin nhắn Telegram để tránh gây hiểu nhầm là bot đã đăng nhập tài khoản thầu của doanh nghiệp.
  - Phải kiểm tra động trạng thái đăng nhập hoặc ghi rõ `Trạng thái: Khách vãng lai (Công khai)`.
- Cronjob schedule: `0 8 * * *` (8:00 AM daily).

### Bilingual & Synonymous Keyword Partitioning for Medical E-HSMT (Updated 2026-10-01)
- **Pitfall**: In Vietnamese procurement notices (E-HSMT), hospitals use divergent terminology across tenders. If a watchdog searches only loanwords (e.g. `stapler`) or only Vietnamese phrasing (e.g. `cắt khâu`), major bidding packages will be silently dropped.
- **User Instruction / Partner Demand**: "Lấy đúng tên để tra thầu: Stapler điện nội soi dùng một lần, Dụng cụ cắt khâu thẳng và băng gim, Trocar".
- **Standard 5-Group Keyword Partitioning in `muasamcong_daily_watchdog.py`**:
  1. `Trocar`: Tra cứu toàn bộ các loại Trocar phẫu thuật nội soi (5mm, 10mm, 12mm, 15mm không dao, có bóng, quang học).
  2. `stapler`: Bắt các gói thầu dùng thuật ngữ quốc tế hoặc tên thương mại ("Powered Laparoscopic Stapler", "Stapler cắt khâu nội soi").
  3. `cắt khâu`: Bắt các gói thầu dùng thuật ngữ tiếng Việt chuẩn y tế ("Dụng cụ cắt khâu thẳng nội soi gập góc", "Dụng cụ khâu cắt nối thẳng dùng pin/cơ").
  4. `băng ghim`: Bắt các gói mua sắm đạn ghim rời ("Băng ghim", "Đạn ghim", "Băng đạn ghim 45/60mm", "Băng gim").
  5. `bảo vệ vết mổ`: Bắt các gói thầu dụng cụ đa cổng SILS và ống bảo vệ vết thương (FGD-1 đến FGD-5).
- Mỗi nhóm được quét độc lập với DOM evaluation và trích xuất `Chưa đóng thầu (\d+)`, ghi nhận structured telemetry metric `[TELEMETRY_METRIC]` và lưu trữ lịch sử tại `muasamcong_history.jsonl`.

## Quality Gate: User Check "Xong hết chưa kiểm tra kĩ lại chưa"
When user asks to double check completion:
1. Map every original request from user images and text against verified deliverables.
2. Verify physical files on disk: verify openpyxl load without corruption, check sheet names, row counts, and data formatting.
3. Verify cronjobs in `cronjob(action='list')` with valid script path and next run time.
4. Provide a structured matrix mapping each requirement to its concrete artifact, plus a ready-to-forward message tailored for the user's partner/collaborator.

## Advanced reCAPTCHA v2 & SSO Authenticator Handling via Chrome CDP (Updated 2026-10-02)

### 1. reCAPTCHA v2 Anchor Frame Direct WebSocket Execution (Bypass Hang & Timing Pitfall)
- **Bẫy Playwright Fonts & Locator Timeout**:
  - Khi dùng Playwright gắn vào CDP (`connect_over_cdp`), các lệnh như `page.screenshot()` hoặc locator click trên iframe reCAPTCHA thường bị treo (`TimeoutError: Page.screenshot: Timeout 5000ms exceeded ... waiting for fonts to load...`) do trang auth của Mua Sắm Công tải phông chữ từ CDN ngoài bị chậm hoặc CSP chặn.
- **Giải pháp Direct WebSocket Target**:
  - Chrome mở riêng một sub-target cho iframe reCAPTCHA (`url` chứa `https://www.google.com/recaptcha/api2/anchor?ar=1&k=...`).
  - Quét `http://127.0.0.1:9222/json/list` để lấy `webSocketDebuggerUrl` của chính iframe anchor đó.
  - Kết nối trực tiếp vào WebSocket của iframe và chạy:
    ```javascript
    document.getElementById('recaptcha-anchor')?.click();
    ```
  - Với profile Chrome thật của user có độ trust cao, `aria-checked` sẽ lập tiếp chuyển từ `"false"` sang `"true"` trong vòng 1-2 giây, tự động inject token mã hóa vào `#g-recaptcha-response` trên trang form cha mà không cần giải câu đố hình ảnh.

### 2. Large WebSocket Payload Framing Pitfall (RFC 6455 Frame Fragmentation)
- **Bẫy stdlib asyncio / cdp_eval**:
  - Script tự chế `cdp_eval.py` dùng socket RFC 6455 thô đơn giản không hỗ trợ frame reassembly khi Chrome gửi các frame phân mảnh (fragmented frames).
  - Khi gọi `Page.captureScreenshot`, payload base64 PNG có kích thước lớn (>60KB - 2MB), dẫn đến socket chỉ đọc được 1 phần frame, `json.loads` thất bại và hàm trả về `None`, gây crash: `TypeError: 'NoneType' object is not subscriptable` khi đọc `shot['result']['data']`.
- **Giải pháp chuẩn hóa**:
  - Với các lệnh cần nhận payload lớn (như screenshot hoặc dump HTML DOM), BẮT BUỘC sử dụng package chuẩn `websockets`:
    ```python
    import websockets
    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        await ws.send(json.dumps({'id': 1, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
        res = json.loads(await ws.recv())
        img_bytes = base64.b64decode(res['result']['data'])
    ```

### 3. SSO 2FA Google Authenticator Automation Flow
- **Quy trình 2 bước trên Mua Sắm Công**:
  - Bước 1: Điều hướng `https://muasamcong.mpi.gov.vn/c/portal/login?p_l_id=141451` -> điền `username` (`vn0402332245`), `password` -> click direct anchor reCAPTCHA -> submit `#kc-login`.
  - Bước 2: Hệ thống chuyển sang URL `.../login-actions/authenticate?execution=...` với form `id="kc-otp-login-form"`, hiển thị nhãn "Xác thực thông tin (Google Authenticator)" và ô input `id="otp"`.
  - Giữ nguyên tab ở màn hình này (không đóng tab hay reload làm hủy session code), chụp screenshot Gate 6 gửi user (`MEDIA:<path>`) để xin mã 6 số OTP.
  - Ngay khi user gửi OTP, chạy script một chạm `submit_otp.py <otp_code>`: điền vào `#otp` và click `#kc-login` để hoàn tất đăng nhập vào Contractor Dashboard.

### 4. Incident 2026-10-02: Bẫy Báo Cáo Sai Lệch (False Negative) do Bỏ Sót YCBG
- **Hiện tượng**: User chất vấn gay gắt *"Vẫn tự cho bot quét đầy đủ chứ, báo cáo chuẩn hay láo v"*.
- **Nguyên nhân cốt lõi**:
  - Script watchdog trước đó chỉ tìm kiếm ở chế độ radio `Số TBMT / Tên gói thầu` (`notifyNo,bidName`) và dùng regex `Chưa đóng thầu (\d+)`.
  - Bệnh viện Nguyễn Trãi đăng Yêu cầu báo giá `RQ2600056970-00` (Băng ghim cho dụng cụ cắt khâu thẳng) còn hạn đến 11/10/2026 trong tab `Yêu cầu báo giá` (`ycbg`), nhưng bot lại kết luận: *"Tất cả các gói thầu tìm thấy đều đã đóng thầu. Chưa có gói mới nào mở nhận hồ sơ"* -> Suýt làm lỡ cơ hội chào thầu của doanh nghiệp.
- **Khắc phục**:
  - Tách bạch và quét tuần tự cả 2 radio: TBMT (`notifyNo,bidName`) và YCBG (`ycbg`).
  - Phân loại parser: TBMT bắt `Chưa đóng thầu (N)`, YCBG bắt `Chưa hết hạn nhận báo giá`.
  - Đọc trạng thái đăng nhập thực tế từ `localStorage` thay vì hardcode thông tin tài khoản doanh nghiệp.

### 5. Public Portal vs Authenticated Session & 24h Token TTL Trap (User Rule 2026-10-02)
- **Bẫy Hết Hạn Phiên 24h (SSO Token TTL)**:
  - Cổng Mua Sắm Công sử dụng Keycloak OpenID Connect với thời hạn sống của `access_token` và `id_token` đúng **24 giờ** (`exp - iat = 86400s`).
  - Sau 24h không tương tác hoặc hết hạn phiên, máy chủ SSO tự động hủy session và ép đăng nhập lại: Mật khẩu + reCAPTCHA + Mã OTP 2FA (Google Authenticator).
- **User Frustration Signal**:
  - *"Ủa vẫn chrome cdp trc t từng login tài khoản mà nay nó ép phải login nhập 2fa lại ag"* và *"Chắc chắn mở công khai k cần tài khoản chứ. Vì mỗi lần login phải nhờ ổng lấy mã mất công"*.
  - User rất phiền lòng khi bot watchdog tự động hàng ngày mà lại bắt người điều hành phải đi xin mã OTP 2FA từ đối tác mỗi ngày.
- **Quy tắc phân định Public Mode vs Authenticated Mode**:
  - **PUBLIC / GUEST MODE (Khách vãng lai - Dùng cho Watchdog/Cron hàng ngày)**:
    - Theo Luật Đấu thầu 2023, 100% dữ liệu mời thầu, danh mục vật tư y tế, thời hạn nhận hồ sơ và **file đính kèm E-HSMT / PDF Yêu cầu báo giá** (nút `.tags-fileAttach`) đều được **MỞ CÔNG KHAI TOÀN DÂN**.
    - Watchdog tự động hàng ngày **BẮT BUỘC CHẠY Ở CHẾ ĐỘ PUBLIC CÔNG KHAI**. Không yêu cầu đăng nhập, không làm phiền user xin OTP 2FA.
  - **AUTHENTICATED MODE (Chỉ kích hoạt khi có yêu cầu đặc thù)**:
    - Chỉ đăng nhập tài khoản nhà thầu khi: (1) Nộp hồ sơ dự thầu / nộp báo giá trực tuyến; (2) Cần mở khóa thông tin liên hệ cá nhân (SĐT/Email) của cán bộ bệnh viện phụ trách tiếp nhận.

### 6. Omnibus Multi-lot Tender Blindspot & Robotic vs Manual Trocar Domain Evaluation (Updated 2026-10-02)

#### A. Bẫy Bỏ Sót Gói Thầu Nhiều Phần/Lô Tên Chung (Omnibus Multi-lot Blindspot)
- **Vấn đề**: Các bệnh viện lớn (như BV Bình Dân, Chợ Rẫy, Bạch Mai...) thường phát hành các gói thầu tổng hợp quy mô lớn mang tên chung:
  * Ví dụ: *"Cung cấp Vật tư y tế Gói 9 năm 2026 (gồm 9 phần (lô), 25 mặt hàng)"* (Mã TBMT: `IB2600553497-00`).
- **Điểm mù của Bot**:
  * Nếu bot watchdog chỉ tìm kiếm từ khóa (`Trocar`, `cắt khâu`) ở ô input `Số TBMT / Tên gói thầu`, hệ thống sẽ **HOÀN TOÀN BỎ LỌT** gói thầu này vì chữ "Trocar" không nằm ở tên gói mà nằm sâu trong danh mục 9 phần/lô của E-HSMT.
  * Các bên mời thầu còn thường gõ sai chính tả (ví dụ: `Troca` thiếu chữ `r`, `băng gim` thay vì `băng ghim`), khiến bộ lọc so khớp chuỗi chính xác bị lọt lưới.

#### B. Kỹ Thuật Trích Xuất Sâu Danh Mục Phân Lô O(1) qua Vue State & Webform (`dtlHsmt`)
- Trên trang chi tiết gói thầu Mua Sắm Công (`contractor-selection?render=detail-v2`), dữ liệu phân lô không nằm ở DOM HTML tĩnh mà được lưu trong state Vue của component `.view-detail`:
  ```javascript
  const dtlHsmt = document.querySelector('.view-detail')?.__vue__?.$data?.dtlHsmt;
  const c4 = dtlHsmt?.bidoInvBiddingDTO?.find(item => item.formCode === 'BD.MT.02.1281');
  const table = JSON.parse(c4.formValue).Table;
  const lots = table.filter(item => item.lotNo && item.lotNo.startsWith('PP')).map(l => ({
      lotNo: l.lotNo,
      lotName: l.lotName,
      price: l.lotPrice
  }));
  ```
- Kỹ thuật này trích xuất toàn bộ danh mục 9 phần/lô (`PP2600411835`, `PP2600411836`...) kèm đơn giá dự toán từng lô chỉ trong < 0.5s mà không cần cào HTML hay tải PDF.

#### C. Cơ Chế Click Lọc Active Tab "Chưa đóng thầu (N)" (Chống Mù Trang 2+)
- Khi tìm kiếm từ khóa bao quát (như `phẫu thuật nội soi` ra 442 kết quả, trong đó có 6 gói Chưa đóng thầu):
  * Mặc định hệ thống hiển thị tab `Tất cả (442)`, trang 1 chỉ toàn gói cũ đã đóng thầu.
  * Nếu không click tab lọc, bot sẽ chỉ đọc trang 1 và kết luận sai là không có gói nào mở.
  * **Giải pháp**: Khi `openCount > 0`, tự động click vào tab `Chưa đóng thầu (N)`:
    ```javascript
    const btn = Array.from(document.querySelectorAll('span, a')).find(e => e.innerText && e.innerText.startsWith('Chưa đóng thầu'));
    if (btn) btn.click();
    ```
  * Mua Sắm Công sẽ lọc ngay toàn bộ N gói đang mở lên đầu danh sách để trích xuất Mã TBMT, Tên gói, Bệnh viện và Hạn đóng thầu.

#### D. Cơ Chế Bắt Gói Tên Chung qua Phân Hệ KHLCNT (`planNo,name`)
- Phân hệ KHLCNT tìm kiếm trên cả trường **"Tóm tắt công việc chính của gói thầu"**.
- Dù tên gói là *"Gói 9 năm 2026"*, nhưng tóm tắt công việc ghi rõ *"vật tư cho hệ thống phẫu thuật nội soi bằng robot"*, KHLCNT sẽ bắt được mã kế hoạch `PL...`.
- Trường `Số thông báo liên kết` trong KHLCNT trỏ thẳng tới mã TBMT `IB...` và hiển thị trạng thái `Đã có TBMT`.

#### E. Phân Định Kỹ Thuật: Trocar Phẫu Thuật Nội Soi Robot vs Trocar Thủ Công (YCCMED)
Khi hệ thống hoặc AI phân tích tính khả thi dự thầu cho dải sản phẩm Trocar YCCMED, BẮT BUỘC nắm vững các ranh giới kỹ thuật sau:
1. **Hệ thống phẫu thuật nội soi Robot (vd: Robot da Vinci) vs Phẫu thuật nội soi thông thường (Manual):**
   * **Trocar Robot**: Là bộ trocar và phụ kiện chuyên dụng tích hợp cơ cấu ngàm khóa cơ học, vòng đệm chịu lực và cổng kết nối ăn khớp với cánh tay robot phẫu thuật. Giá trị gói rất lớn (lên tới hàng tỷ đồng/lô do là vật tư đi theo hệ thống máy độc quyền).
   * **Trocar YCCMED (Thủ công / Cầm tay)**: Là trocar dùng một lần phục vụ phẫu thuật nội soi ổ bụng tiêu chuẩn, thao tác trực tiếp bằng tay của phẫu thuật viên.
2. **Quy cách kích thước (Size mismatch):**
   * Trocar Robot thường yêu cầu kích thước riêng biệt của cánh tay robot: **8 mm** và **10 mm**.
   * Dải Trocar YCCMED chỉ có các cỡ tiêu chuẩn: **5 mm, 10 mm, 12 mm, 15 mm** (HOÀN TOÀN KHÔNG CÓ CỠ 8 mm).
3. **Tiêu chuẩn kỹ thuật Chương V E-HSMT:**
   * Các tiêu chí như nòng tù không lưỡi, van silicone kép chống xì CO2, chiều dài thân 100 mm của trocar thủ công thông thường không thể đáp ứng tiêu chí kỹ thuật của trocar robot.
   * **Kết luận nghiệm thu thầu**: Nếu gói thầu yêu cầu trocar dùng cho hệ thống robot, phân loại ngay là **KHÔNG PHÙ HỢP (Trượt kỹ thuật)**, không tốn tài nguyên lập E-HSDT.

#### F. Triển Khai Quét Đủ 3 Phân Hệ Mời Thầu: TBMT, YCBG và CGTTRG
- Ngoài TBMT (`notifyNo,bidName`) và YCBG (`ycbg`), Mua Sắm Công có phân hệ thứ 3: **TBMT chào giá trực tuyến rút gọn** (`cgttrg` - `input[type="radio"][value="cgttrg"]`).
- Đây là hình thức mua sắm trực tuyến nhanh mà các cơ sở y tế thường xuyên áp dụng cho vật tư tiêu hao (cắt khâu, trocar, đạn ghim).
- Watchdog `muasamcong_daily_watchdog.py` bắt buộc quét tuần tự cả 3 phân hệ này trong mỗi chu kỳ để tránh điểm mù.

#### G. Bẫy Từ Khóa Quá Rộng (Noise/Spam Trap) vs Bộ Từ Khóa Chuyên Môn Y Tế Chuẩn
- **Sự cố & Bài học xương máu (2026-10-02)**:
  * Khi mở rộng từ khóa tìm kiếm sang cụm từ chung chung như `phẫu thuật nội soi`, bot bị **bội thực gói rác (False Positives)**: Nó gom cả những gói mua **máy móc thiết bị phần cứng** (dàn hệ thống máy nội soi, tủ sấy dụng cụ kim loại, dao cắt đốt tiền liệt tuyến...), trong khi doanh nghiệp chỉ kinh doanh **vật tư tiêu hao**.
  * User bức xúc phản hồi: *"Chưa hiểu nãy m bảo mấy gói đó k đủ điều kiện h lại đi báo cả đống"*.
  * **Quy tắc cứng**: CẤM đưa từ khóa cấp chuyên khoa/máy móc (`phẫu thuật nội soi`) vào ô tìm kiếm tự động; từ khóa BẮT BUỘC phải gắn liền với nhóm vật tư tiêu hao mục tiêu.

#### H. Đặc Tả Nghiệp Vụ Chuẩn: Trocar YCCMED - Công Ty Nguyên Thuận (System Prompt Contract)
Khi quét và thẩm định thầu cho Công ty Nguyên Thuận, BẮT BUỘC bám sát đặc tả kỹ thuật sau:
1. **Dải từ khóa chuyên môn y khoa đầy đủ**:
   - `trocar`, `trocal`, `trocar nội soi`, `trocar ổ bụng`, `dụng cụ chọc tạo đường vào`, `dụng cụ xuyên chọc`, `ống trocar`, `cannula`, và `gói dụng cụ phẫu thuật nội soi có mặt hàng trocar`.
2. **Quy chuẩn kỹ thuật Trocar YCCMED**:
   - **Đặc tính bắt buộc**: Dùng một lần, **không lưỡi dao** (bladeless), **không bóng cố định**, **thân ren** (threaded), chiều dài thân **100 mm**.
   - **Đúng 4 Model tiêu chuẩn (Size match)**:
     * `5X100-6.0` (cỡ 5 mm)
     * `10X100-11.11` (cỡ 10 mm)
     * `12X100-13.0` (cỡ 12 mm)
     * `15X100-16.0` (cỡ 15 mm)
   - Nếu gói yêu cầu cỡ khác (vd: 8mm Robot) hoặc có bóng, có dao -> Đánh giá ngay: **KHÔNG PHÙ HỢP / TRƯỢT KỸ THUẬT**.
3. **Cấu trúc trường thông tin xuất ra cho mỗi gói mở**:
   - Mã TBMT, ngày đăng/cập nhật, tên gói, bệnh viện, mặt hàng, số lượng, có dao/không dao, có bóng/không bóng, kích thước, hạn đóng thầu, trạng thái, liên kết nguồn.
4. **Quy chuẩn câu thông báo khi không có gói mới**:
   - Bắt buộc ghi đúng câu: **“Hôm nay chưa có gói trocar mới”** kèm nhắc ngắn các cơ hội còn hạn.

#### I. Kiến Trúc Hybrid: Crawler Python Thuần vs LLM Evaluator (Chống Rớt Session Plus)
- **Không cắm tài khoản Web ChatGPT Plus vào bot tự động**: Gói Plus cá nhân dùng token/cookie web rất dễ bị Cloudflare quét văng session sau 2-3 ngày, gây gián đoạn và phiền hà cho người dùng không rành kỹ thuật.
- **Mô hình Hybrid 2 tầng tối ưu**:
  1. *Tầng 1 (Python thuần gác cổng mỗi sáng)*: Mở Chrome CDP quét sạch 3 phân hệ (TBMT, YCBG, CGTTRG). 99% ngày không có gói mở -> Python tự kết luận trong 15-50s, tốn 0đ tiền AI và 0 token.
  2. *Tầng 2 (LLM thẩm định E-HSMT khi có gói)*: CHỈ KHI bắt trúng gói thầu đang mở thực tế, bot mới gọi LLM (Claude/GPT) đọc file E-HSMT để đối soát 4 model YCCMED và sinh bản phân tích chuyên sâu.

#### J. Kỷ Luật Soạn Tin Nhắn Cho User Trả Lời Đối Tác / Sếp
- **Không giảng giải chuyện cũ**: Khi đối tác đã gửi ảnh chụp màn hình phân tích rõ ràng từ ChatGPT, họ đã nắm toàn bộ thông tin đó. CẤM nhắc lại hoặc phân tích lại gói cũ họ đã biết (tránh bị user mắng: *"Ổng đã nhắn cái hình ChatGPT phân tích rồi còn đi nhắc lại"*).
- **Ngắn gọn, súc tích (1-2 câu)**: Đi thẳng vào thông tin mới hoặc câu chốt kỹ thuật, văn phong tự nhiên, khiêm tốn, không vòng vo.
- **Không bao giờ nói "gửi code" cho đối tác kinh doanh**: Đối tác là dân kinh doanh/bán hàng, chỉ quan tâm báo cáo kết quả trên Telegram. CẤM nói "em gửi code cho anh xem", phải nói "để bot bắn báo cáo qua Telegram cho anh kiểm tra".

#### K. Ủy Thác Nâng Cấp Code Qua Claude Code CLI trên Windows
- **Vị trí file script chuẩn**: `muasamcong_daily_watchdog.py` nằm tại `%LOCALAPPDATA%\hermes\scripts\` (`C:\Users\Kibe\AppData\Local\hermes\scripts\`), TUYỆT ĐỐI KHÔNG tìm trong `D:\Taadaa` (Cursor / IDE ngoài thường quét nhầm `D:\Taadaa` và báo không thấy file).
- **Quy trình dispatch Claude Code CLI**:
  1. Kiểm tra tài khoản Pro CLI: `claude auth status --text`.
  2. Viết toàn bộ prompt đặc tả nghiệp vụ chi tiết ra file prompt tạm (ví dụ `claude_task_prompt.md`).
  3. Khởi chạy Claude Code Print Mode ngầm:
     `claude -p "Please read <prompt_file> and implement..." --allowedTools "Read,Edit,Write,Bash" --max-turns 15` kèm `background=True, notify_on_complete=True, timeout=300`.
  4. Sau khi Claude Code hoàn thành (exit 0):
     - Kiểm tra cú pháp: `python -m py_compile muasamcong_daily_watchdog.py`.
     - Xóa file prompt tạm.
     - Chạy bộ kiểm thử: `pytest D:/Taadaa/tools/tests/test_muasamcong_and_stock_closeout.py` (đảm bảo 8/8 PASSED).
     - Chạy nghiệm thu thực tế (Live dry-run) qua background terminal và đối soát telemetry `telegram_sent status 200` cùng event `tender_reported` / `known_open` trong `muasamcong_history.jsonl`.



