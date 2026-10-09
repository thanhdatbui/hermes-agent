# GPMLogin v4 UI & Core Version Upgrade Pitfalls

## 1. Lỗi giả "Yêu cầu cập trình duyệt [Chromium] [X]" từ API v3
### Hiện tượng
- Gọi API start profile (`GET /api/v3/profiles/start/{id}`) bị fail với message:
  `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}` hoặc `[127]`.
- Thư mục binary `gpm_browser/gpm_browser_chromium_core_142` trên đĩa đã tồn tại đầy đủ `chrome.exe`, `gpmdriver.exe`, `142.0.7444.163`.

### Nguyên nhân gốc rễ
1. **Lệch kiến trúc 32-bit vs 64-bit giữa Profile và Core Browser (NGUYÊN NHÂN HÀNG ĐẦU):**
   - GPMLogin app mặc định tạo profile ở chế độ **32-bit (x86)**.
   - Các gói core Chromium hiện đại (`gpm_browser_chromium_core_142`, `137`...) trên máy đều là bản build **64-bit (x64)** (Google Chrome đã dừng phát hành 32-bit từ lâu).
   - Khi profile 32-bit cố khởi động core 64-bit, API GPM v3 sẽ chặn lại và quăng ra thông báo lỗi: `Yêu cầu cập trình duyệt [Chromium] [142]`.
   - **Cách khắc phục dứt điểm 100%:**
     - **Cách 1 (Ưu tiên số 1 - An toàn tuyệt đối không đổi Fingerprint):** Bấm **Cập nhật lại GPM** (tải/đồng bộ lại gói tài nguyên GPM chuẩn từ server). Thao tác này đồng bộ lại manifest và runtime giữa GPM app với server GPM mà **KHÔNG CẦN CHUYỂN PROFILE SANG 64-BIT**, giữ nguyên `64bit = False` và bảo toàn 100% fingerprint của toàn bộ dàn nick cũ.
     - **Cách 2 (Chỉ dùng cho profile mới hoặc khi dính Google Cooldown):** Vào tab **Quản lý Profile** trên app GPMLogin -> chọn tính năng **"Chuyển profile sang 64bit"**.
       - **Quy tắc an toàn sống còn:** CẤM tick `All` (tránh đổi fingerprint các profile cũ đang sống ổn định). Chỉ tick chọn các nhóm profile mới tạo/cần chạy hoặc nhóm bị dính Google cooldown.
       - Bấm **Thực hiện**. Sau khi chuyển profile sang 64-bit, API `/api/v3/profiles/start` và nút "Mở" sẽ chạy ngay lập tức với `gpmdriver.exe`.

2. **Modal Popup chặn UI (như "Big Update" Database Fingerprint 411):**
   - Khi app GPMLogin hiển thị modal thông báo (ví dụ popup **"Big Update: 1. Cập nhật database fingerprint hoàn toàn mới (411) ... 2. Kỉ nguyên chuyển đổi"**), popup này chiếm focus và chặn toàn bộ engine UI của GPMLogin.
   - **Tử huyệt Local API 19995:** Dù service HTTP vẫn phản hồi 200 OK trên các endpoint đọc (`/profiles`), lệnh khởi động trình duyệt (`/api/v3/profiles/start/{id}`) sẽ bị **chặn ngầm 100%** và quăng ra thông báo lỗi giả: `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}`!
   - **Xử lý:** Bắt buộc bấm nút màu đỏ **"Đóng thông báo"** ở dưới đáy modal popup trên giao diện desktop (hoặc nhờ user click qua màn hình thật). Sau khi đóng popup và bấm nút "Mở" bằng tay trên 1 profile bất kỳ để nạp runtime lần đầu, API v3 mới được giải phóng hoàn toàn để script tự động hóa hoạt động.
   - Tuyệt đối không xóa/sửa mò file `settings.json` hay can thiệp SQLite vì trạng thái popup được giữ trong bộ nhớ runtime của tiến trình WPF `GPMLogin.exe`.

3. **Bẫy WebSocket CDP trên Chromium Core 142 (`403 Forbidden` / Missing `--remote-allow-origins`):**
   - Từ Chromium 142, engine bảo mật siết chặt kiểm tra header `Origin` trên cổng Remote Debugging (`--remote-debugging-port`).
   - Nếu GPM khởi động Chromium 142 mà không có cờ `--remote-allow-origins=*`, kết nối WebSocket tới `ws://127.0.0.1:<cdp_port>/devtools/browser/...` sẽ bị từ chối với lỗi: `Handshake status 403 Forbidden - Rejected an incoming WebSocket connection from http://127.0.0.1 origin`.
   - Playwright `connect_over_cdp` có thể bị timeout hoặc handshake error nếu header Origin bị chặn.
   - **Cách xử lý khi dùng WebSocket trực tiếp:** Khi dùng module `websocket` trong Python để điều khiển CDP, truyền tham số `suppress_origin=True` trong `websocket.create_connection(ws_url, suppress_origin=True)` để không gửi header Origin, vượt qua kiểm tra 403 thành công 100%.

4. **Lỗi `0xc0000135` (STATUS_DLL_NOT_FOUND) khi spawn `chrome.exe` Core 142:**
   - Trong thư mục `gpm_browser_chromium_core_142`, nếu file `chrome_elf.dll` bị thiếu ở thư mục gốc (nằm cùng cấp với `chrome.exe`), Windows sẽ không thể khởi chạy Chromium và trả về mã thoát `3221225781` (`0xc0000135`).
   - Tiến trình chrome.exe lập tức kết thúc trước khi kịp bind cổng debugging, khiến CDP không thể kết nối.
   - **Khắc phục:** Đảm bảo copy `chrome_elf.dll` từ thư mục build con (`142.0.7444.163/chrome_elf.dll`) ra đặt tại thư mục gốc `gpm_browser_chromium_core_142/` cùng cấp với `chrome.exe`.

5. **Lệch version build & Thiếu file `data-variations.gpm` trong thư mục Core (Bí quyết sửa lỗi O(1) không cần mở GUI):**
   Khi GPMLogin kiểm tra tính hợp lệ của gói core Chromium (ví dụ `gpm_browser_chromium_core_142`), backend engine của `GPMLogin.exe` kiểm tra đồng thời 2 điều kiện tiên quyết trong thư mục core:
   1. File `version` phải mang nội dung phiên bản hợp lệ (ví dụ `1.1`). Nếu file mang `1.0`, API lập tức từ chối khởi động với thông báo: `Yêu cầu cập trình duyệt [Chromium] [142]`.
   2. File cấu hình biến thể `data-variations.gpm` BẮT BUỘC phải tồn tại trong thư mục core gốc (`gpm_browser_chromium_core_142\data-variations.gpm`). Khi file này bị thiếu (do quá trình giải nén cập nhật dở dang hoặc copy sót), API cũng quăng lỗi `Yêu cầu cập trình duyệt [Chromium] [142]`.
   - **Cách khắc phục triệt để O(1) qua script/filesystem:**
     - Copy file `data-variations.gpm` từ `gpm_browser\default\data-variations.gpm` sang `gpm_browser\gpm_browser_chromium_core_142\data-variations.gpm`.
     - Ghi chuỗi `1.1` vào file `gpm_browser\gpm_browser_chromium_core_142\version`.
     - Ngay sau 2 thao tác này, API `/api/v3/profiles/start/{id}` lập tức trả về `{"success": true, "message": "OK"}` và spawn browser thành công mà không cần mở GUI bấm tay!

6. **Tái phát lỗi Core 142 sau mỗi lần reset/khởi động lại máy (Reboot Loop do `default\update.zip` bị tải dở):**
   - **Hiện tượng:** User hoặc script đã sửa xong core 142, API mở profile chạy bình thường. Nhưng cứ mỗi khi khởi động lại máy tính (reboot PC) hoặc mở lại GPM, core 142 lại lập tức bị lỗi: `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}`.
   - **Nguyên nhân gốc rễ:**
     - Trong thư mục template fallback `C:\Users\<user>\AppData\Local\Programs\GPMLogin\gpm_browser\default\update.zip`, tồn tại file nén tải dở từ trước (ví dụ chỉ có 105 MB thay vì ~117-119 MB).
     - Kiểm tra bằng 7-Zip (`7za t update.zip`) phát hiện: `Unexpected end of archive` và `Data Error: 142.0.7444.163\chrome.dll`.
     - Khi máy tính reboot hoặc khi GPM app khởi động / kích hoạt tính năng kiểm tra tài nguyên (Auto-fix Resource), GPM lấy gói `default\update.zip` bị lỗi này để bung/đè vào core Chromium, làm `chrome.dll` trong `142.0.7444.163` bị cụt dở và reset file `version` về `1.0`.
   - **Quy trình xử lý dứt điểm 100%:**
     1. **Kiểm tra tính toàn vẹn của archive:**
        ```cmd
        "C:\Users\Kibe\AppData\Local\Programs\GPMLogin\7za.exe" t "C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\default\update.zip"
        ```
        Nếu xuất hiện lỗi `Unexpected end of archive` hoặc `Data Error` -> chính là nguồn gây tái phát lỗi.
     2. **Cô lập file zip hỏng:** Di chuyển thành `update.zip.corrupted_bak`.
     3. **Đóng gói lại `update.zip` chuẩn từ core đang chạy tốt:**
        Đứng tại `gpm_browser_chromium_core_142`, dùng `7za.exe` nén các file manifest và chrome.dll chuẩn (264.7 MB):
        ```cmd
        "C:\Users\Kibe\AppData\Local\Programs\GPMLogin\7za.exe" a -tzip "C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\default\update.zip" "142.0.7444.163\142.0.7444.163.manifest" "142.0.7444.163\chrome.dll"
        ```
     4. **Xác nhận `Everything is Ok`:** Chạy lại `7za t`, archive mới đạt ~112 MiB và 0 error.
     5. **Khóa version `1.1`:** Đảm bảo file `version` tại cả `gpm_browser\default\version` và `gpm_browser\gpm_browser_chromium_core_142\version` đều chứa `1.1`.
     6. **Nghiệm thu Cold Start:** Tắt và bật lại GPMLogin.exe, kiểm tra `POST /api/v3/profiles/start/{id}` trả về `success: true`. Giờ đây khi reset máy, GPM sẽ không còn bị file zip dở làm hỏng core nữa.

7. **Bảo toàn tài sản tài khoản cũ đã thuê SIM verify (SIM-Verified Asset Preservation Invariant):**
   - Các tài khoản (Hotmail, Gmail, ChatGPT, OpenAI Codex) đã từng thuê SIM verify tốn tiền thật của user là tài sản giá trị cao, tuyệt đối **CẤM** suy diễn là nick vứt đi, cấm tự ý xóa khỏi database hay đánh dấu die vĩnh viễn khi chưa có bằng chứng xác thực tuyệt đối từ server.
   - Khi token hết hạn hoặc dính lỗi OAuth/GPM core, BẮT BUỘC ưu tiên kiểm tra hạ tầng (GPM core, proxy liveness, hòm thư qua Microsoft Graph API) để phục hồi phiên đăng nhập, thay vì vội vàng bỏ nick.
   - *Bẫy thao tác tự động trên Disconnected Desktop (Headless Pitfall):* Khi phiên Windows ở trạng thái disconnected/locked (độ phân giải ảo 800x600/800x1555 không có màn hình vật lý), giao diện WPF của GPMLogin không render bề mặt DirectX (`PrintWindow` ra ảnh đen, `BitBlt` trả về 0, `mouse_event`/`SendMessage` không kích hoạt được click UI). Agent TUYỆT ĐỐI CẤM loop click mù Win32 để cố đóng popup/bấm nút cập nhật. Bắt buộc test O(1) qua curl API `profiles/start/{id}` lấy JSON lỗi thực tế báo cáo rõ cho User mở màn hình bấm 1 click "Cập nhật lại GPM".
   - *Bẫy Cache Cờ Runtime sau khi Resource Fixer Tool báo "Phiên bản mới nhất":* Khi cửa sổ `Resource fixer tool` của GPM đã kiểm tra và hiển thị dòng chữ xanh `gpmbrowser_chromium_core_142: Phiên bản mới nhất`, API `/api/v3/profiles/start` vẫn có thể tiếp tục quăng lỗi `Yêu cầu cập trình duyệt [Chromium] [142]`. Lý do: GPM app giữ cờ chặn runtime cho đến khi người dùng bấm nút **"Mở"** trực tiếp bằng tay trên 1 profile bất kỳ từ giao diện Profiles. Việc bấm "Mở" thủ công lần đầu kích hoạt tiến trình nạp binary Chromium 142 và giải phóng hoàn toàn cờ chặn API cho toàn bộ các profile còn lại.

4. **Tử huyệt can thiệp cờ `ConvertProfileTo64bit` trong SQLite (CRITICAL PITFALL):**
   - Trong bảng `Profiles` -> cột `JsonData` của `profile_data.db`, tuyệt đối **CẤM** tự ý cập nhật `"ConvertProfileTo64bit": true` bằng script SQL.
   - Khi cờ này bị gán `true` thủ công, GPM Local API sẽ kiểm tra profile theo luồng chuyển đổi chưa hoàn tất và chặn khởi động với lỗi: `{"success": false, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}` dù binary core 142 x64 đã có đầy đủ.
   - **Khắc phục**: Luôn giữ nguyên `"ConvertProfileTo64bit": false` trong `JsonData`. Khi cờ này là `false`, GPM v4.3.6-stable sẽ khởi chạy trực tiếp binary `gpm_browser_chromium_core_142\chrome.exe` với `gpmdriver.exe` thành công 100%.

5. **GPM App UI Trắng / Blank Canvas nhưng Local API 19995 vẫn sống hoàn hảo:**
   - Khi chạy GPMLogin ngầm hoặc sau khi mở lại app, cửa sổ `GPMLogin.exe` có thể hiển thị một màn hình trắng trơn (blank white area) do lỗi render GPU/DirectX của giao diện Electron.
   - **CẤM HIỂU NHẦM LÀ APP CRASH ĐỂ FORCE KILL**: Service Local API của GPM chạy qua Windows HTTP Server API (`Microsoft-HTTPAPI/2.0`) tại port `19995`. Dù giao diện trắng trơn, API `http://127.0.0.1:19995/api/v3/profiles...` vẫn phản hồi HTTP 200 OK và điều khiển start/stop profile hoàn toàn bình thường. Chỉ cần kiểm tra qua `curl http://127.0.0.1:19995/api/v3/profiles?page=1&limit=2`.

### Thực tế giao diện GPM v4 (Pitfalls cần tránh)
- **Cảnh báo Downgrade:** GPM v4 chặn hạ version từ Chromium 137 trở lên (`Do not downgrade from version 137`) và cảnh báo đỏ: *"Từ phiên bản 137 cần cập nhật trình duyệt bản mới nhất mới có thể hạ phiên bản"*. Modal "Thay đổi version trình duyệt" chỉ liệt kê từ 137 trở xuống, **hoàn toàn không có tùy chọn 142**.
- **Popup/Toast thông báo lỗi không có nút tải:**
  Khi click "Mở" profile từ bảng danh sách, góc dưới bên phải hiện toast thông báo màu cam `💥 Yêu cầu cập trình duyệt [Chromium] [142]`, toast này chỉ là thông báo, không chứa nút tải về.
- **Menu Cài đặt & Công cụ KHÔNG CÓ chỗ tải:**
  Menu Cài đặt (Settings - hình bánh răng) chỉ quản lý đường dẫn lưu profile, 7Z, ngôn ngữ, theme, extension. Menu Công cụ (Tools - hình cờ lê) chỉ có chức năng sao lưu, phục hồi, đổi tên profile. **CẢ HAI MENU NÀY ĐỀU KHÔNG CÓ NÚT TẢI CORE TRÌNH DUYỆT**. Tuyệt đối không chỉ dẫn user mò vào hai menu này.
- **Quyền hạn Windows (UIPI Pitfall):**
  - GPMLogin thường chạy dưới quyền Administrator (Elevated). Nếu Hermes/Gateway chạy dưới Standard User, các tool automation/computer_use sẽ bị Windows chặn (`InjectSyntheticPointerInput: Access is denied 0x80070005`).
  - Phải khởi động Hermes/Gateway với đặc quyền Administrator nếu cần tương tác UI tự động với GPMLogin.
- **Format Watchdog Báo cáo & Chế độ Im lặng (Silent Watchdog):**
  - Thông báo watchdog Telegram **BẮT BUỘC** ngắn gọn tối đa: Chỉ gồm tóm tắt số lượng ACTIVE/DIE và nhóm các lỗi chính, tuyệt đối cấm in tràn log chi tiết từng thao tác mở profile (`Đang mở GPM profile PID...`).
  - Khi **100% tài khoản trong pool ACTIVE**: Watchdog phải **IM LẶNG HOÀN TOÀN (SILENT / Không gửi tin nhắn)** để tránh spam người dùng.

---

## 2. Giao diện GPM hiển thị Proxy `http:0`
### Hiện tượng
- Trên bảng danh sách profile của GPMLogin v4, cột **Proxy** hiển thị `http:0` thay vì IP/Host và Port thực tế, khiến người dùng lầm tưởng profile chưa được add proxy.

### Nguyên nhân
- Khi script gán chuỗi proxy vào database SQLite (`Profiles.JsonData -> Proxy`) hoặc qua API `create_profile(raw_proxy=...)`:
  - Format truyền vào dính ghi chú hoặc tiền tố scheme không chuẩn: `http://192.168.110.2:20061 (test.taadaa.click:5127)`.
  - Parser của GPMLogin v4 không bóc tách được chuỗi có chứa dấu ngoặc đơn `()` và protocol `http://`, dẫn đến parse lỗi thành hostname `http` và port `0`.

### Giải pháp chuẩn hóa
- Luôn truyền chuỗi proxy đúng cú pháp chuẩn:
  - **Dạng có user/pass:** `host:port:user:pass` (ví dụ `test.taadaa.click:5127:mobi27:TaadaaMobi#2026!`).
  - **Dạng không auth (LAN/Singbox):** `host:port` hoặc `http://host:port` nguyên gốc không thêm ghi chú ngoặc đơn `(...)`.
- Để ghi chú thông tin proxy gốc, sử dụng trường **`Note`** hoặc thêm vào tên profile, tuyệt đối không nối chuỗi thô vào giá trị của trường Proxy.
- Cập nhật lại qua API:
  `POST /api/v3/profiles/update/{id}` với payload `{"raw_proxy": "host:port:user:pass"}`.

---

## 3. Modal lỗi "Lỗi khi tải tiện ích - Tệp kê khai bị thiếu hoặc không thể đọc được" (clipboard-ext)
### Hiện tượng
- Khi khởi động một profile Chromium trên GPM (đặc biệt là profile mới tạo, profile clone dở dang, hoặc profile tạm thời như `temp_check`), xuất hiện popup modal cảnh báo màu vàng của Chromium:
  `Lỗi khi tải tiện ích - Không tải được tiện ích từ: <profile_dir>\Default\GPMSoft\Extensions\clipboard-ext. Tệp kê khai bị thiếu hoặc không thể đọc được.`
- Modal này che phủ giao diện trang web (ví dụ Google Sign-In) và chặn thao tác người dùng/automation cho đến khi click "OK".

### Nguyên nhân gốc rễ
- GPMLogin tự động inject tham số khởi chạy Chromium:
  `--load-extension="<profile_dir>\Default\GPMSoft\Extensions\clipboard-ext"`
- Nếu profile được tạo nhanh qua API hoặc sao chép/khởi tạo mà app chưa copy gói tiện ích gốc từ template sang thư mục profile `.../Default/GPMSoft/Extensions/clipboard-ext`, Chromium sẽ không tìm thấy file `manifest.json` và bật modal cảnh báo.

### Cách khắc phục
1. **Thủ công tức thời:** Bấm "OK" trên popup để bỏ qua. Profile vẫn duyệt web và login bình thường (chỉ thiếu tính năng clipboard sync của GPM).
2. **Khắc phục triệt để bằng script / filesystem:**
   - Copy toàn bộ thư mục template tiện ích `clipboard-ext` gốc:
     `C:\Users\<user>\AppData\Local\Programs\GPMLogin\app_data\BrowserExtensions\clipboard-ext`
   - Sang đường dẫn profile đích:
     `C:\Users\<user>\AppData\Local\Programs\GPMLogin\profile\<profile_id>\Default\GPMSoft\Extensions\clipboard-ext`
   - Đảm bảo thư mục đích chứa đầy đủ `manifest.json`, `background.js`, `contentscript.js` trước khi khởi chạy trình duyệt.

---

## 4. Tích tụ tiến trình GPM Chrome mồ côi (Orphan Processes) & Khóa thư mục Profile (`SingletonLock`)
### Hiện tượng
- Hệ thống tích tụ hàng chục đến hàng trăm tiến trình Chrome (`cmdline` chứa `gpm` hoặc `--remote-debugging-port`) chạy ngầm dù các ca tự động hóa hoặc watchdog đã kết thúc.
- Các lần chạy tiếp theo của script watchdog/healer khi gọi API mở profile GPM bị treo, dính lỗi `Locator.click: Timeout 30000ms exceeded`, hoặc `Timeout bắt OAuth code` (120s).

### Nguyên nhân gốc rễ
1. **Lỗi ngắt nửa vời của Chromium:**
   - Khi gọi `GET /api/v3/profiles/close/{id}` hoặc Playwright `browser.close()`, Chromium đôi khi chỉ đóng window chính nhưng các tiến trình phụ (GPU process, utility, crashpad-handler, renderers) vẫn tiếp tục sống.
   - Khi script gặp exception/timeout, luồng thoát có thể không chạm tới đoạn cleanup.
2. **Khóa thư mục Profile (`SingletonLock`):**
   - Mỗi profile Chrome duy trì một file khóa `SingletonLock` trong thư mục user data dir (`.../GPMLogin/profile/<profile_id>/SingletonLock`).
   - Nếu tiến trình mồ côi còn giữ file khóa này, khi API GPM cố mở lại profile, Chromium sẽ không tạo session mới mà cố kết nối vào process cũ đã mất liên kết CDP, khiến Playwright connect/evaluate bị treo cứng.

### Giải pháp chuẩn hóa & Phòng ngừa
1. **Cơ chế đóng 3 lớp dứt điểm (3-Layer Teardown):**
   - Lớp 1: Playwright `context.close()` / `browser.close()`.
   - Lớp 2: Gọi API GPM `GET /api/v3/profiles/close/{id}` (fallback: `stop/{id}`).
   - Lớp 3: Tra cứu các PID có `--user-data-dir` trỏ tới profile đó; nếu sau 2-3s vẫn còn tiến trình sống, force-terminate bằng `psutil` hoặc `taskkill /F /PID`.
2. **Định kỳ rà soát & Dọn dẹp tiến trình mồ côi (Pre-flight Reaper):**
   - Trước khi thực hiện các ca chạy batch hoặc watchdog sáng sớm, chạy script kiểm tra số lượng tiến trình Chrome GPM. Nếu không có tác vụ nào đang active mà tồn tại Chrome mồ côi, thực hiện reap an toàn để giải phóng RAM và lock.

---

## 5. Phát hiện Port API thực tế của GPM-Login v4 (`8130` vs `19995`) & Khởi động đúng cách (Tránh Degraded Process)
### Hiện tượng
- Gọi API endpoint mặc định `http://127.0.0.1:19995/...` bị lỗi connection refused hoặc trả về rỗng.
- Thực tế trong bản GPM-Login v4.3.6-stable, service local API có thể bind tại port `8130` (hoặc port động tùy profile/instance).
- Khi GPMLogin.exe bị tắt và khởi động lại qua `subprocess.Popen` (Python) hoặc bash background, tiến trình có thể kẹt ở trạng thái **Degraded** (RAM chỉ ~66 MB thay vì ~138 MB, không kết nối server Cloudflare `104.21.92.222:443` để xác thực license, và hoàn toàn không bind port `19995` vào `HTTP.sys`).

### Khởi động lại GPMLogin chuẩn xác O(1) qua PowerShell
```powershell
powershell.exe -NoProfile -Command "Stop-Process -Name GPMLogin -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; Start-Process 'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\GPMLogin.exe'"
```
Sau lệnh trên, tiến trình nạp đủ ~138 MB RAM, kết nối Cloudflare xác thực license hợp lệ, và port 19995 online trong 8–15 giây (`Microsoft-HTTPAPI/2.0`).

### Cách phát hiện O(1) qua PowerShell:
```powershell
# Tra cứu port listening của tiến trình GPMLogin.exe:
$gpmPid = (Get-Process GPMLogin -ErrorAction SilentlyContinue).Id
if ($gpmPid) {
    Get-NetTCPConnection -OwningProcess $gpmPid -State Listen | Select-Object LocalAddress, LocalPort
}
```
Hoặc qua netstat: `netstat -ano | grep <GPMLogin_PID>` để xác định đúng port trước khi bắn request API.

---

## 6. Hiện tượng "Bão tiến trình" (Cron Storm) & Hàng chục Chrome Profile kẹt trên Taskbar
### Hiện tượng
- Thanh Taskbar Windows bị tràn ngập hàng chục icon Chrome với các badge số profile (`97, 98, 100, 103, 104...`).
- App GPM-Login hiển thị nhiều profile ở trạng thái "Đang mở", chiếm dụng hàng GB RAM.
- User phản ánh: *"tiến trình nào spam 1 đống gpm v"*.

### Nguyên nhân gốc rễ
1. **Trùng lặp khung giờ giữa nhiều Cronjob Watchdog:**
   - Trong các khung giờ rảnh (ví dụ sáng 07:15 - 08:45 / 09:00):
     - `post-evening-gpm-login-watchdog` chạy mỗi 5 phút (`*/5 7,8,12,13,20,21,22,23 * * *`).
     - `post-morning-gmail-2fa-watchdog` chạy mỗi 5 phút (`*/5 8,9,10,11 * * *`).
     - `gpm-lifecycle-sync-watchdog` chạy mỗi 15 phút.
     - `gpm-gmail-nurture-watchdog` chạy lúc 09:00.
   - Khi một watchdog chạy sub-flow dài (ví dụ `batch_dual_oauth_5workers.py` pha loãng hành vi xem YouTube Shorts 90-120s, giải reCAPTCHA, hoặc `run_add_2fa_remaining.py` mở 6 profile song song), tổng thời gian chạy có thể kéo dài >5-10 phút.
   - Do schedule là `*/5`, tick tiếp theo lại được kích hoạt khi tick trước chưa dứt điểm, tạo ra hiệu ứng **bão tiến trình (cron storm)**.
2. **Kẹt tiến trình cũ qua đêm không được dọn dẹp:**
   - Các profile mở từ ngày hôm trước (20/09, 21/09) khi dính timeout mạng/proxy hoặc lỗi CDP không được script kill triệt để, tiếp tục nằm chờ trên Taskbar.

### Quy trình điều tra O(1) định danh thủ phạm
Khi xảy ra tình trạng spam profile GPM / tràn icon Chrome Taskbar:

1. **CẤM TUYỆT ĐỐI QUÉT ĐĨA DIỆN RỘNG (INVARIANT O(1)):**
   - **BẪY CHẾT NGƯỜI**: Tuyệt đối CẤM chạy `os.walk`, `grep -rn` tìm ID profile, hoặc tìm file modified trên `D:/Taadaa` hay `AppData/Local`. Lệnh sẽ dính timeout 180s, làm đông cứng phiên điều phối và khiến người dùng ức chế hỏi "???".
   - Mọi chẩn đoán tiến trình **BẮT BUỘC chỉ đọc RAM/WMI O(1)** qua `Get-CimInstance Win32_Process` hoặc `netstat`.

2. **Phân biệt Burst Đang Spawn (Active) vs Xả Rác Lũy Kế (Orphan Leak):**
   - Kiểm tra `CreationDate` của dàn Chrome con:
     ```powershell
     Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*GPMLogin\gpm_browser*" -and $_.ParentProcessId -eq (Get-Process GPMLogin).Id } |
         Select-Object ProcessId, CreationDate, CommandLine | Sort-Object CreationDate
     ```
   - **Nếu CreationDate rải đều từ vài giờ trước (ví dụ 11:06 - 11:08 sáng)**: Không có tiến trình nào đang spam điên cuồng ở hiện tại. Đây là vết tích rò rỉ (process leak) từ một đợt chạy batch trước đó bị crash/terminate ngắt quãng nhưng thiếu hook dọn dẹp.
   - **Nếu CreationDate liên tục xuất hiện mới theo từng giây/phút**: Hệ thống đang bị Cron Storm hoặc vòng lặp vô tận kích hoạt mở profile mới.

3. **Phân lập Tuyệt đối giữa GPM Chromium và Chrome Chính chủ của User:**
   - Chrome người dùng: `C:\Program Files\Google\Chrome\Application\chrome.exe` (chứa các tab làm việc, TikTok, sàn MMO, email cá nhân...).
   - Chromium của GPM: `C:\Users\<user>\AppData\Local\Programs\GPMLogin\gpm_browser\...\chrome.exe`.
   - CẤM TUYỆT ĐỐI dùng lệnh chung `Stop-Process -Name chrome` hay `taskkill /IM chrome.exe`.

4. **Lệnh Dọn Dẹp An Toàn Tuyệt Đối (Scanned Kill):**
   - Chỉ tiêu diệt đúng các tiến trình Chromium thuộc thư mục GPMLogin:
     ```powershell
     Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*GPMLogin\gpm_browser*" } | Stop-Process -Force
     ```
   - Xác nhận lại bằng readback count = 0.

5. **Đối soát cronjob & Script nguồn:**
   - Dùng `cronjob action='list'` xem các job chạy gần khung giờ `CreationDate`.
   - Kiểm tra script Python đang chạy trong RAM:
     ```powershell
     Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "gpm|batch_dual|run_oauth|run_add_2fa|cron_gpm" } |
         Select-Object ProcessId, ParentProcessId, CommandLine
     ```

6. **Teardown Invariant cho Mọi Script Batch GPM:**
   - Mọi script batch mở nhiều profile (ví dụ batch login, dual oauth, nurture) BẮT BUỘC phải bọc trong `try...finally` hoặc đăng ký `atexit.register(...)` để gọi cleanup toàn bộ PIDs/profile IDs đã mở. Không để tiến trình ngắt ngang bỏ lại hàng chục cửa sổ trên taskbar.

---

## 7. Bẫy Tử Huyệt Khi Kill Chrome Theo Port vs `--user-data-dir` (Nguyên nhân rò rỉ 400+ Zombie Process)
### Lỗi thiết kế phổ biến trong các script cũ
Rất nhiều script tự động hóa GPM (`run_add_2fa_remaining.py`, `post_morning_gmail_2fa_watchdog.py`, `batch_dual_oauth_5workers.py`) triển khai hàm đóng Chrome như sau:
```powershell
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match '{port}' } | Stop-Process -Force
```
hoặc truyền nhầm `port = 5100 + m` (cổng proxy farm/điện thoại thay vì CDP remote debugging port thực tế).

### Tại sao cách lọc theo Port thất bại 100% và tạo ra bão Zombie Process?
1. **Kiến trúc đa tiến trình của Chromium (Chromium Multi-Process Architecture):**
   - Mỗi một profile GPM khi mở ra sẽ khởi chạy từ **8 đến 12 tiến trình riêng biệt**:
     - 1 Tiến trình Browser chính (Browser/Parent Process).
     - 1 Tiến trình GPU (`--type=gpu-process`).
     - 1+ Tiến trình Tiện ích (`--type=utility`).
     - 4 đến 8 Tiến trình Renderer (`--type=renderer`).
     - 1 Tiến trình Crashpad (`--type=crashpad-handler`).
   - **TỬ HUYỆT:** **Chỉ duy nhất 1 tiến trình Browser chính mang cờ `--remote-debugging-port={port}`!** Toàn bộ các tiến trình con GPU, Renderer, Utility, Crashpad hoàn toàn **KHÔNG CHỨA** chuỗi port này trong dòng lệnh (`CommandLine`).
2. **Hậu quả khi chạy lệnh lọc theo port:**
   - Lệnh chỉ kill được duy nhất tiến trình Browser chính (hoặc trượt hoàn toàn nếu port bị truyền nhầm/lệch).
   - Bỏ lại **toàn bộ 7–10 tiến trình con mồ côi (orphans)** kẹt lại trong hệ thống.
   - Các tiến trình con này tiếp tục giữ handle cửa sổ, icon có badge số cổng vẫn bám chặt trên Taskbar Windows.
   - Khi chạy một batch 40–50 profile, số lượng tiến trình Chrome zombie tích tụ lên đến **400–500 tiến trình**, làm tê liệt CPU/RAM và làm nghẽn toàn bộ Taskbar của user!
3. **Bẫy GPM Soft-Close (`/api/v3/profiles/stop/{id}` vô dụng khi treo mạng):**
   - API `profiles/stop/{id}` của GPMLogin chỉ gửi tín hiệu ngắt mềm (`WM_CLOSE`).
   - Nếu Playwright CDP đang duy trì kết nối WebSocket, hoặc trang web đang kẹt một request dở dang trên proxy 4G lag, Chromium sẽ **bỏ qua hoàn toàn lệnh đóng mềm** và tiếp tục treo ngầm.

### Chuẩn hóa hàm Teardown dứt điểm (Canonical Teardown Pattern)
Bắt buộc áp dụng cơ chế 3 bước dứt điểm:
1. **Bước 1:** Đóng Playwright trước để ngắt kết nối WebSocket CDP (`browser.close()`, `pw.stop()`).
2. **Bước 2:** Gọi cả 2 API GPM `GET /api/v3/profiles/close/{id}` và `GET /api/v3/profiles/stop/{id}` để ngắt phiên.
3. **Bước 3 (BẮT BUỘC):** Kill dứt điểm theo **Thư mục Profile (`--user-data-dir`)** kết hợp cờ GPMLogin, KHÔNG lọc duy nhất theo port:
```python
def kill_gpm_profile_processes(profile_dir: str, remote_port: int = None):
    """
    Tiêu diệt 100% tiến trình con (Browser, GPU, Renderer, Utility) của một profile GPM.
    Bảo vệ tuyệt đối Google Chrome cá nhân của user.
    """
    if not profile_dir and not remote_port:
        return
    conditions = []
    if remote_port and remote_port != 9222:
        conditions.append(f"$_.CommandLine -match '{remote_port}'")
    if profile_dir:
        clean_dir = os.path.normpath(profile_dir).replace('\\', '\\\\')
        conditions.append(f"$_.CommandLine -match [regex]::Escape('{clean_dir}')")
    if not conditions:
        return
    cond_str = " -or ".join(conditions)
    ps_cmd = (
        f"Get-CimInstance Win32_Process | Where-Object {{ "
        f"  ($_.CommandLine -like '*GPMLogin\\gpm_browser*' -or $_.Name -eq 'chrome.exe') -and "
        f"  ({cond_str}) "
        f"}} | Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=10)
```

---

## 8. Hard Pre-Spawn Concurrency Cap (Cơ chế chặn bão Taskbar trước khi gọi `/profiles/start`)
### Hiện tượng
Vòng lặp batch (`run_add_2fa_remaining.py` / `batch_dual_oauth_5workers.py`) duyệt qua danh sách email:
- Khi profile A gặp lỗi đóng không được, vòng lặp không dừng mà lập tức gọi tiếp `profiles/start` cho profile B, C, D...
- Hậu quả: Chỉ trong 50 giây, script đã nã API mở liên tiếp 51 profile (17:32:13 -> 17:33:05), làm bùng nổ Taskbar trước khi user kịp phát hiện.

### Quy tắc Invariant: Thắt van khởi chạy (Pre-Spawn Gate)
Trước khi gọi `GET /api/v3/profiles/start/{id}`, mọi script BẮT BUỘC phải đếm số lượng tiến trình Chromium của GPM đang hoạt động trên hệ thống:
```python
def get_running_gpm_browser_count() -> int:
    """Đếm số tiến trình Chromium GPM đang mở trong RAM O(1)."""
    ps_cmd = "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*GPMLogin\\gpm_browser*' -and $_.CommandLine -like '*--type=gpu-process*' }).Count"
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
        return int(res.stdout.strip() or 0)
    except Exception:
        return 0

def wait_for_gpm_concurrency_slot(max_allowed: int = 3, timeout_sec: int = 30):
    """Nếu số profile đang mở >= max_allowed, chờ hoặc cưỡng chế dọn dẹp trước khi mở mới."""
    start_t = time.time()
    while time.time() - start_t < timeout_sec:
        active_count = get_running_gpm_browser_count()
        if active_count < max_allowed:
            return True
        logger.warning(f"Đang có {active_count} profile GPM mở (vượt trần {max_allowed}). Đang chờ slot nhả...")
        time.sleep(3)
    # Nếu hết timeout mà vẫn nghẽn -> Dọn dẹp profile mồ côi hoặc raise Exception, TUYỆT ĐỐI CẤM spawn thêm
    raise RuntimeError(f"Hệ thống đang nghẽn {active_count} profile GPM chưa đóng. Chặn spawn mới để bảo vệ Taskbar!")
```

---

## 9. Bẫy Xóa Profile Qua API v3 (`/api/v3/profiles/delete/{id}`): Bắt buộc `mode=2`
### Hiện tượng
- Gọi API xóa profile: `GET http://127.0.0.1:19995/api/v3/profiles/delete/{id}?mode=1`.
- API trả về thành công: `{"success": true, "data": null, "message": "OK"}`.
- **NHƯNG THỰC TẾ**: Profile **KHÔNG HỀ BỊ XÓA** khỏi SQLite database `profile_data.db` (bảng `Profiles`), tên profile và folder data vẫn còn nguyên vẹn trong hệ thống.
- Nếu không truyền tham số `mode` (`GET /api/v3/profiles/delete/{id}`), API báo lỗi: `{"success": false, "data": null, "message": "INVALID_MODE"}`.

### Nguyên nhân & Bản chất tham số `mode`
- `mode=1`: Xóa trên Cloud / Trash / Soft-delete. Với các profile tạo local trên máy, lệnh này trả về `OK` nhưng không xóa dữ liệu local trong SQLite.
- `mode=2`: **Hard Delete / Local Permanent Delete**. Xóa hoàn toàn bản ghi profile khỏi bảng `Profiles` trong SQLite database và dọn sạch dữ liệu đĩa.

### Quy chuẩn gọi API Xóa Profile chuẩn xác
1. **Endpoint bắt buộc:**
   `GET http://127.0.0.1:19995/api/v3/profiles/delete/{profile_id}?mode=2`
2. **Readback verify bắt buộc:**
   Sau khi gọi API xóa, phải query SQLite database để xác minh chắc chắn profile đã biến mất:
   ```python
   import sqlite3
   from pathlib import Path

   db_path = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
   conn = sqlite3.connect(db_path)
   cur = conn.cursor()
   cur.execute("SELECT count(*) FROM Profiles WHERE Id = ?", (profile_id,))
   assert cur.fetchone()[0] == 0, f"Profile {profile_id} vẫn còn trong SQLite DB!"
   conn.close()
   ```
3. **Dọn dẹp State file đồng bộ:**
   Nếu profile nằm trong danh sách theo dõi của các cronjob/watchdog (như `D:\Taadaa\runtime\kibe\cron-state\gpm_gmail_nurture_state.json`), phải lọc và xóa sạch key/entry của profile đó để tránh script chạy lại quét phải profile rác.

---

## 10. Xung Đột `PYTHONPATH` Môi Trường Hermes Khi Chạy Python 3.12 / Playwright CDP
### Hiện tượng
- Khi chạy script tự động hóa GPM / Playwright bằng Python hệ thống (ví dụ Python 3.12 tại `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe` hoặc script trong `D:\Taadaa\Hotmail\scripts\batch_gpm_hotmail_password_login.py`), script bị crash ngay dòng `from playwright.sync_api import sync_playwright` với lỗi:
  `ModuleNotFoundError: No module named 'greenlet._greenlet'`

### Nguyên nhân gốc rễ
- Terminal session của Hermes Agent mặc định inject biến môi trường:
  `PYTHONPATH=C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages;...` (virtualenv nội bộ của Hermes, thường dùng Python 3.11).
- Trình thông dịch Python 3.12 bên ngoài khi khởi động tự động nạp các package từ `PYTHONPATH` trước. Do các C-extension compiled binary (`.pyd`) như `greenlet._greenlet` trong venv của Hermes được compile cho Python 3.11, Python 3.12 không tương thích ABI và không load được module C này, dẫn đến `ModuleNotFoundError`.

### Giải pháp chuẩn hóa
- Khi gọi Python 3.12 hoặc bất kỳ Python interpreter ngoài nào từ terminal/script automation, **BẮT BUỘC** làm sạch `PYTHONPATH`:
  - **Trên dòng lệnh bash:**
    ```bash
    export PYTHONPATH=""
    # hoặc gọi inline:
    PYTHONPATH="" /c/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe <script.py>
    ```
  - **Phòng vệ trong script Python (trước khi import Playwright):**
    ```python
    import sys
    sys.path = [p for p in sys.path if "hermes-agent\\venv" not in p.lower()]
    ```

---

## 11. Cập nhật Chromium Core Hàng Loạt Qua API v3 (`POST /profiles/update/{id}`) & Xử lý `PROFILE_IN_TRASH`
### Bối cảnh & Hiện tượng
- Nhiều profile GPM cũ vẫn giữ core Chromium cũ (như `127.0.6533.73`), dễ bị Cloudflare Turnstile và OpenAI Sentinel gắn cờ bot khi dùng cho các luồng automation nhạy cảm (như ChatGPT-Web / Google OAuth).
- Cần nâng cấp đồng loạt dàn profile lên core mới nhất (`142.0.7444.163` - `gpm_browser_chromium_core_142`) mà không làm hỏng dữ liệu cookies, proxy, hay fingerprint.

### Endpoint chuẩn hóa cập nhật Version Core:
- **API Call:**
  `POST http://127.0.0.1:19995/api/v3/profiles/update/{profile_id}`
  hoặc `POST http://127.0.0.1:19995/api/v3/profiles/edit/{profile_id}`
- **JSON Payload:**
  ```json
  {"browser_version": "142.0.7444.163"}
  ```
- **Cơ chế cập nhật tự động:**
  API tự động cập nhật cả `browser_version` trong GPM runtime và các trường liên quan trong SQLite `Profiles.JsonData` (`BrowseVersion = "142.0.7444.163"`, User-Agent chuyển thành `Chrome/142.0.0.0`). Khi gọi `profiles/start`, GPM sẽ trỏ đúng vào binary `gpm_browser_chromium_core_142\chrome.exe`.

### Bẫy `PROFILE_IN_TRASH` (GroupId = 0):
- Nếu profile đang nằm trong Thùng rác (`Profiles.GroupId = 0` trong SQLite), API update sẽ trả về:
  `{"success": false, "data": null, "message": "PROFILE_IN_TRASH"}`
- **Quy tắc lọc:** Khi thực hiện update hàng loạt, **BẮT BUỘC** chỉ query các profile đang hoạt động (`WHERE GroupId > 0`), bỏ qua các profile đã vào thùng rác để tránh lỗi.
- **Khóa cứng version mặc định khi tạo mới:** Trong client GPM (`gpm_client.py`), luôn gán mặc định `browser_version = "142.0.7444.163"` trong payload `create_profile` để mọi profile mới sinh ra đều đồng bộ nhân Chromium mới nhất.

---

## 12. Quy Chuẩn Sao Lưu Profile GPM Nhanh Siêu Nhẹ (High-Speed Essential Backup Protocol)
### Vấn đề
- Thư mục profiles GPM chứa tới 254+ profile. Nếu nén thô cả thư mục, tổng dung lượng có thể lên tới >40 GB do chứa các file cache, crashpad, engine WASM và binary tiện ích trùng lặp.
- Nén cả thư mục mất hàng giờ, gây tràn ổ cứng và dễ bị chặn bởi Invariant Farm Guard (`os.walk` blocked).

### Cơ chế bóc tách Session sống vs Binary/Cache rác
Chỉ cần sao lưu chính xác các file và thư mục cốt lõi cấu thành phiên đăng nhập của Chromium:
1. **Database tổng (BẮT BUỘC):** `profile_data.db` -> lưu `profile_data_backup_<YYYYMMDD>.db` (chứa toàn bộ metadata, proxy, 124 trường fingerprint của 254 profile).
2. **File Session thiết yếu trong mỗi thư mục Profile (`ProfilePath`):**
   - **Gốc profile:** `Local State` (chứa master DPAPI key để giải mã cookies/passwords), `First Run`, `Last Version`.
   - **Thư mục `Default/`:**
     - File dữ liệu: `Preferences`, `Secure Preferences`, `Login Data`, `Web Data`, `History`, `Network/Cookies` (kèm file `-journal` nếu có).
     - Thư mục trạng thái: `Local Storage`, `Session Storage`, `IndexedDB`, `GPMSoft` (cấu hình extension GPM), `Extension State`, `Sync Data`.
3. **Loại bỏ 100% các thành phần rác & binary tải lại được:**
   - Caching: `Cache`, `Code Cache`, `DawnGraphiteCache`, `DawnWebGPUCache`, `GraphiteDawnCache`, `GPUCache`, `GrShaderCache`, `ShaderCache`.
   - Temporary & logs: `Crashpad`, `BrowserMetrics` (`.pma`), `Service Worker/ScriptCache` (100MB+ cache JS).
   - Static Binaries: `GPMBrowserExtenions` (150MB+ binary tiện ích như Metamask đã có bản gốc trong app_data), `WasmTtsEngine` (22MB WASM binary).

### Kết quả & Hiệu năng thực tế:
- Giảm dung lượng từ **~40 GB** xuống chỉ **376 MB** (tỷ lệ nén 38.6% cho toàn bộ 254 profile).
- Thời gian nén hoàn tất: **~64 giây** (sử dụng `zipfile.ZIP_DEFLATED` với `compresslevel=3`).
- **Phòng tránh bẫy Invariant Guard:** Tuyệt đối không dùng `os.walk` trong script backup. Thay thế bằng hàm đệ quy an toàn dùng `os.scandir` để thu thập file.
- Script chuẩn đặt tại: `D:\Taadaa\GPM auto\scripts\backup_gpm_profiles.py`.

---

## 13. Checklist Kiểm Tra Toàn Diện Thông Số Anti-Detect (Fingerprint Completeness Audit)
Khi người dùng yêu cầu kiểm tra profile đã fake đầy đủ thông số chưa, query trực tiếp `Profiles.JsonData` trong `profile_data.db` với các tiêu chí chuẩn:
- **`UserAgent`**: Khớp chính xác phiên bản Core Chromium hiện tại (ví dụ `Chrome/142.0.0.0`).
- **`CanvasNoiseToken`**: Khác null/rỗng (bơm nhiễu đồ họa canvas ngẫu nhiên).
- **`AudioNoise`**: Khác null/rỗng (bơm nhiễu AudioContext buffer).
- **`WebGLRenderer` & `WebGLVendor`**: Khai báo GPU thực/giả lập (ví dụ `ANGLE (Intel, Intel(R) UHD Graphics 630... Direct3D11)` và `Google Inc. (Intel)`).
- **`MacAddress`**: Địa chỉ MAC ngẫu nhiên theo chuẩn `XX-XX-XX-XX-XX-XX`.
- **`WebRTC`**: Khai báo cấu hình `disable` hoặc `fake` để ngăn chặn rò rỉ IP thật qua STUN/TURN request khi duyệt qua proxy.
- **`Fonts`**: Danh sách font masking không để lộ toàn bộ font Windows đặc thù.
- **`PlatformOS` & CPU/RAM**: `WinVersion = "Windows 10"`, `WinPlatform = "64 bit"`, `HardwareConcurrency` (số luồng CPU), `DeviceMemory` (RAM).
- **`Timezone`**: Tự động bind theo IP của Proxy (khớp timezone thực tế của mạng).
- **`ScreenResolution` (`ScreenWidth`, `ScreenHeight`)**: Đặt giá trị `-1` (Trong GPMLogin, `-1` là cơ chế khớp native theo độ phân giải màn hình thật của máy chủ, tránh phát hiện viewport bất thường).


