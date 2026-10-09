# Quy trình Tuyển chọn Ứng viên & Nạp OAuth Cổng Chưa Chạy (Untouched Ports)

## 1. Bối cảnh & Mục tiêu
Khi mở rộng và bổ sung target cho combo `ag-gemini-pool-3` trên OmniRoute (:20129) từ dàn máy Samsung S7 (Farm Taadaa), việc nạp hàng loạt cần tuân thủ nghiêm ngặt nguyên tắc cách ly cổng proxy, chống checkpoint và không gây đứt gãy hệ thống.

## 2. Tiêu chí Tuyển chọn An toàn (Safety Preflight)

### 2.1. Port Isolation (1 Account / 1 Port / 1 Ngày)
- Mỗi cổng proxy 4G vật lý (Mobi 5101..5138 hoặc MikroTik 10001..10035) chỉ chạy tối đa 1 tài khoản trong ngày.
- Loại trừ ngay lập tức các cổng đã chạy thành công hôm nay (ghi nhận trong `config/oauth_pipeline_status.json` hoặc nhật ký phiên, ví dụ Port 5123, 5137, 16002).
- **Rà soát xung đột Port chia sẻ giữa các máy (Multi-Machine Port Sharing)**: Trong farm, nhiều máy S7 dùng chung 1 cổng proxy (ví dụ M24 & M62 cùng dùng Port 5128; M32 & M70 cùng dùng Port 5138; M08 & M46 cùng dùng Port 5108; M29 & M67 cùng dùng Port 5135). BẮT BUỘC kiểm tra không có bất kỳ máy nào trong cặp chia sẻ port đã chạy hôm nay trước khi chọn ứng viên.
- **Đối soát trực tiếp Combo đang chạy (`GET /api/combos`)**: Không chỉ dựa vào gợi ý sơ bộ. Ví dụ Port 5104 (M42) có thể đã được nạp tài khoản `yenduypham2002997@gmail.com` vào `ag-gemini-pool-3` từ phiên trước (vị trí `pool-29`). Bắt buộc query `GET http://127.0.0.1:20129/api/combos` và kiểm tra toàn bộ target để loại bỏ các cổng đã có account active trong combo.

### 2.2. Độ tuổi Ngâm An toàn (Soak Age $\ge$ 3 ngày) & Bẫy Excel Serial Date
- Chỉ chọn tài khoản có ngày tạo $\le$ T-3 ngày (ví dụ chạy ngày 07/09/2026 thì ngày tạo $\le$ 2026-09-04).
- Các tài khoản mới tạo trong ngày hoặc ngâm chưa đủ 3 ngày trên thiết bị Android S7 tuyệt đối không đưa vào pipeline, vì Google sẽ kích hoạt kiểm tra số điện thoại (SMS checkpoint `challenge/iap`).
- **Bẫy định dạng ngày trong Excel (`gmail_clean_v2.xlsx`)**: Cột `ngày tạo` thường lưu số nguyên ngày nối tiếp của Excel (Excel Serial Date, ví dụ `46177`, `46183`, `46222`). Trong hệ lịch Excel (gốc 1899-12-30), `46177` = 10/06/2026, `46183` = 16/06/2026. Đây là các tài khoản mốc vàng đã ngâm gần 3 tháng trên điện thoại thật. Khi parse ngày bằng Python, cần kiểm tra: nếu giá trị là số nguyên `isinstance(val, (int, float)) and 40000 <= val <= 50000`, đây là tài khoản đã ngâm cực lâu (đạt chuẩn 100%), tránh loại nhầm do lỗi parse string datetime.

### 2.3. Ưu tiên Tài khoản đã có sẵn Profile GPM (`profile_data.db`) & Phân luồng 2FA vs No-2FA
- Tra cứu bảng `Profiles` trong `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`:
  `SELECT Id, Name, ProfilePath, JsonData FROM Profiles`
- Khi tuyển chọn tài khoản từ danh sách ứng viên thỏa mãn port isolation, **phân biệt rõ 2 nhóm trạng thái kỹ thuật**:
  1. *Đã có Profile GPM + Đã có 2FA Secret* (như M29 `sJQe8QqdWh-02092026`): Đạt chuẩn tuyệt đối để đưa thẳng vào `run_oauth_s7_pipeline.py` (chạy Chromium -> approve Prompt/TOTP -> OAuth -> Combo).
  2. *Đã có Profile GPM nhưng CHƯA có 2FA Secret* (như M60 `12-8801320930664_zhqmw` - `crystalwwilsonlypp1@gmail.com`): **TUYỆT ĐỐI KHÔNG CHẠY TRỰC TIẾP `run_oauth_s7_pipeline.py`**. Nếu gọi OAuth ngay khi chưa bật Xác minh 2 bước, Google sẽ redirect thẳng về `signin/rejected?rrk=77` và khóa Cooldown 7 ngày! Tài khoản này bắt buộc phải đi qua luồng kích hoạt 2FA trước (`run_full_pipeline_2fa_and_oauth.py` với `need_enable_2fa: True`) trong cùng persistent context rồi mới thực hiện OAuth.
  3. *Đã có 2FA Secret nhưng CHƯA có Profile GPM* (như M39 `tachau17042004@gmail.com` trong `master_gmail_manager.xlsx`): Cần tạo profile GPM tương ứng qua GPM Local API (`POST /api/v3/profiles/create` với raw proxy `test.taadaa.click:5101...`) trước khi mở Playwright, tránh lỗi thư mục profile không tồn tại.

### 2.4. Kỷ Luật Prune Thư Mục & Tra Cứu Tránh Bẫy Timeout 900s & Lỗi Ripgrep MSYS Path
- Tuyệt đối KHÔNG chạy `find / -name ...` hoặc `os.walk('D:\Taadaa')` / `glob.glob` đệ quy không giới hạn trên thư mục gốc `D:\Taadaa` hay `C:\Users\Kibe`. Thư mục này chứa hàng chục nghìn file trong `node_modules`, `Hermes\.venv`, `BACKUP_ALL`, sẽ khiến lệnh bị timeout và đốt cạn sạch số lượng tool call cho phép của phiên làm việc.
- **Bẫy đường dẫn MSYS trên Ripgrep (`/d/...` vs `D:/...`)**: Khi dùng công cụ tìm kiếm file hoặc ripgrep trên Windows, truyền đường dẫn kiểu POSIX `/d/Taadaa/...` sẽ gây lỗi `os error 3 (The system cannot find the path specified)`. Luôn dùng định dạng Windows `D:/...` hoặc `D:\...`.
- Quy tắc tra cứu O(1):
  - Toàn bộ script pipeline và runner tập trung tại: `D:\Taadaa\GPM auto\scripts\` (`run_oauth_s7_pipeline.py`, `append_to_combo_pool3.py`, `add_oauth_omniroute.py`).
  - Tra cứu proxy & máy S7: Đọc trực tiếp `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (sheet `Proxy`).
  - Tra cứu tài khoản Gmail & 2FA: Đọc trực tiếp `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`, `Master_All`) và `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
  - Tra cứu Profile GPM: Truy vấn SQLite trực tiếp `profile_data.db` (chỉ mất 0.05s).
  - Nếu bắt buộc walk thư mục: Luôn đặt bộ lọc loại trừ:
    `dirs[:] = [d for d in dirs if d not in ('node_modules', '.venv', 'BACKUP_ALL', '.git', 'runtime', 'context-worktrees')]`.

### 2.4. Nạp Credentials & Profile Trực Tiếp Vào `acc` Dict (Tránh Bẫy `get_creds` & `KeyError: 'profile'`)
- Hàm `get_creds(email)` trong `run_oauth_s7_pipeline.py` chỉ đọc sheet `Kibe_Farm_S7` của `master_gmail_manager.xlsx`. Nhiều tài khoản sạch (ví dụ M32 `huynh.cong.loan05@gmail.com`) nằm ở `gmail_clean_v2.xlsx`.
- Nếu runner không truyền trực tiếp `password` và `totp_secret` trong dictionary `TARGETS = [{"mid": ..., "password": "...", "totp_secret": "..."}]`, `get_creds` trả về rỗng khiến Playwright kẹt im lặng khi gặp `challenge/pwd` hoặc `challenge/totp`. BẮT BUỘC inject đầy đủ `password` và `totp_secret` vào `acc` dict.
- **Bẫy `KeyError: 'profile'` & Lệch Tên Thư Mục Profile**: Hàm `process_account(acc)` đọc trực tiếp `prof_dir = os.path.join(GPM_BASE, acc["profile"])`. Nếu không có key `"profile"`, script sẽ crash ngay lập tức. Ngoài ra, thư mục profile của máy S7 thường mang tên theo máy hoặc email cũ (ví dụ M61 mang tên folder `SUNVqFew4a-05092026`, M35 mang tên `nIR8rge0kw-05092026`), nên truy vấn SQLite `profile_data.db` theo email mới sẽ không tìm thấy. BẮT BUỘC map cứng hoặc truyền tường minh trường `"profile": "<folder_name>"` cho từng máy trong danh sách `TARGETS`.

### 2.3. Loại trừ Đa tầng (Multi-Layer Blacklist)
- **Cooldown 7 ngày (`rrk=77`)**: Không chạm vào các máy/tài khoản dính thông báo *"Thêm tính năng Xác minh 2 bước trong phần cài đặt rồi thử lại sau 7 ngày nữa"* (M20, M21, M22, M23, M28, M50).
- **Hạ nhiệt IP (`ip_cooling_recaptcha`)**: Bỏ qua các máy đang tạm dừng để nguội IP do dính reCAPTCHA ảnh puzzle (M10, M59, M68).
- **Lỗi mật khẩu/Checkpoint cũ (`wrong_password_or_checkpoint`)**: Bỏ qua các tài khoản đã ghi nhận lỗi mật khẩu hoặc đòi SMS từ trước (M36, M38, M65).
- **Mail khôi phục rủi ro**: Loại trừ 100% tài khoản có recovery chứa `khoale` hoặc `khoaleemagic`.
- **Đã nạp thành công**: Bỏ qua tài khoản đã có trong `omniroute_success`.

### 2.4. Xác thực Phần cứng Thực tế (Hardware Ground Truth qua ADB `dumpsys account`)
- Không phụ thuộc hoàn toàn vào file Excel (`gmail_clean_v2.xlsx`, `master_gmail_manager.xlsx`).
- Trước khi chạy Playwright, BẮT BUỘC chạy kiểm tra nhanh O(1) không bật màn hình:
  ```bash
  adb -s <serial> shell dumpsys account | grep -i "<email>"
  ```
- Chỉ khi tài khoản thực sự tồn tại trong danh sách Google Account trên S7 thì mới kích hoạt Playwright. Điều này ngăn chặn triệt để lỗi lệch serial máy khiến Google Prompt (`challenge/dp`) nảy trên máy khác và script kẹt timeout 180s.

### 2.6. Kiểm tra Singbox Proxy Egress Theo Machine ID (Cạm Bẫy Công Thức Cũ)
- **Quy tắc Singbox Port Mapping Chuẩn (Verified 2026-09-08)**:
  - Cổng Singbox trên `192.168.110.2` được cấu hình theo **MACHINE ID**:
    $$\text{Singbox Port} = 20000 + \text{Machine ID (mid)}$$
    *(Ví dụ: Máy 19 $\rightarrow$ `20019`, Máy 24 $\rightarrow$ `20024`, Máy 40 $\rightarrow$ `20040`, Máy 46 $\rightarrow$ `20046`, Máy 49 $\rightarrow$ `20049`, Máy 54 $\rightarrow$ `20054`, Máy 68 $\rightarrow$ `20068`, Máy 70 $\rightarrow$ `20070`)*.
  - **Cạm bẫy công thức cũ**: Tránh dùng `20000 + (port - 5100)` vì công thức này chỉ đúng với Máy 1–8. Với Máy > 8 (như Máy 19 port 5123), công thức cũ tính ra `20023` gây `WinError 10054` (Connection Reset).
  - BẮT BUỘC khai báo rõ ràng `"singbox_port": 20000 + mid` trong dictionary `acc`.
- Kiểm tra kết nối trước khi khởi động Playwright:
  ```python
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
      b = p.chromium.launch(headless=True)
      page = b.new_page(proxy={"server": f"http://192.168.110.2:{sb_port}"})
      r = page.goto("https://accounts.google.com/ServiceLogin", timeout=5000)
      assert r and r.status == 200
      b.close()
  ```
- Kiểm tra `proxyId` trên OmniRoute qua `GET /api/settings/proxies` để đảm bảo cổng proxy đã được khai báo sẵn sàng cho bước gán 1:1.

### 2.7. Xử lý Lỗi reCAPTCHA Loading Subtree Interception & Audio Challenge Lockout
- **Hiện tượng**: Khi gặp reCAPTCHA trên proxy mới hoặc trust score nhạy cảm, checkbox `#recaptcha-anchor` có thể ở trạng thái `recaptcha-checkbox-loading` / `recaptcha-checkbox-disabled` kèm lớp `<div>` overlay chặn pointer events. Playwright chờ 30 giây và báo lỗi `Timeout 30000ms exceeded`.
- **Audio Challenge Lockout**: Nếu Google phát hiện IP bất thường và khóa audio challenge ("Your computer or network may be sending automated queries"), nút `#recaptcha-audio-button` sẽ không thể click, dẫn đến timeout 180s (`status: TIMEOUT`).
- **Xử lý An Toàn trong Batch**:
  - Script runner bọc try...except để không làm sập toàn bộ batch.
  - Gom toàn bộ các máy đạt `SUCCESS` / `ALREADY_SUCCESS` trong batch (ví dụ M62, M33) để append đồng loạt vào combo `ag-gemini-pool-3` qua `append_connections()`.
  - Các tài khoản dính timeout (như M32, M46) được lưu ảnh debug screenshot, cách ly và đưa vào diện hạ nhiệt IP (`ip_cooling_recaptcha`), tuyệt đối không cố gắng retry dồn dập trên cùng một cổng proxy trong ngày.

## 3. Quy trình Nạp & Bổ sung Combo (Parallel 2 Worker & Continuous Runner)

1. **Chiến lược Scale Song Song 2–3 Worker (`delegate_task(tasks=[...])`)**:
   - Khởi chạy song song 2 worker độc lập, mỗi worker xử lý 1 tài khoản trên 1 máy S7 và 1 cổng proxy riêng biệt.
   - Rút ngắn thời gian mỗi mẻ từ 4-5 phút xuống còn ~1.5–2 phút.
   - CẤM scale quá 4–5 worker để tránh nghẽn USB modem và kích hoạt bot-check reCAPTCHA diện rộng.
2. **Quy chuẩn Đặt Tên Profile GPM Gom Cụm (User Directive 2026-09-08)**:
   - Định dạng chuẩn: `M<mid:02d> - <port> - <email>` (ví dụ: `M49 - 5113 - chuloan02122003@gmail.com`).
   - Giúp sắp xếp theo cột Name trên GPM gom gọn từng cụm máy/port liền kề nhau, dễ quản lý $O(1)$.
3. **Circuit Breaker**: Dừng batch ngay nếu gặp 2 lỗi liên tiếp để bảo vệ dàn tài khoản.
4. **Incremental Append vào `ag-gemini-pool-3`**:
   - Gọi `append_connections` trong `append_to_combo_pool3.py` ngay sau mỗi tài khoản thành công (tránh gom cuối batch).
   - **CẤM TUYỆT ĐỐI ĐỔI TÊN COMBO** (giữ nguyên `name: "ag-gemini-pool-3"`).
   - Lọc trùng connection ID trước khi append.
   - Sao lưu ngay sang `D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json`.
5. **Xử lý Cờ Cảnh Báo `• degraded` Trên OmniRoute Do Thiếu `projectId`**:
   - Khi exchange token, Google đôi khi không trả về `projectId`, khiến connection bị đánh cờ đỏ/vàng `degraded` ("Google Cloud Code projectId could not be found").
   - **Khắc phục ngay**: Gửi `PUT /api/providers/{cid}` với `{"projectId": "aicode-consumers", "providerSpecificData": {"clientProfile": "ide", "projectId": "aicode-consumers", "tier": "free-tier"}}`, sau đó gọi `POST /api/providers/{cid}/sync-models`. Cờ cảnh báo sẽ biến mất và tài khoản xanh lá 100% (`• đã kết nối`).
6. **Quy Chuẩn Nghiệm Thu Proof Screenshot Bắt Buộc (User Approved 2026-09-08 — "Chuẩn rồi, sau cứ chụp thế này")**:
   - **BẮT BUỘC CUỘN XUỐNG ĐÁY DANH SÁCH (Bottom of Antigravity List)**:
     - Dùng Playwright mở URL: `http://127.0.0.1:20129/dashboard/providers/antigravity`.
     - Tài khoản mới thêm LUÔN nằm ở cuối bảng. Dùng `scroll_into_view_if_needed()` cuộn các account mới nhất ở cuối vào giữa màn hình.
     - Chụp ảnh màn hình rõ ràng hiển thị các accounts mới nhất (chấm xanh đã kết nối, email mask, proxy gán).
     - Gửi ảnh qua cú pháp `MEDIA:<path>`.
   - **CẤM TUYỆT ĐỐI**:
     - CẤM gửi ảnh màn hình điện thoại Samsung S7 làm proof (User rejected: *"Ủa mày log in lên gpm thành công thì gửi ảnh của profile gpm chứ gửi ảnh s7 chi vậy"*).
     - CẤM gửi ảnh màn hình tab callback bị `ERR_CONNECTION_RESET` / `502 Bad Gateway` (User rejected: *"Này ảnh lỗi r, do oauth xong link bị lỗi"*).
     - CẤM chụp lửng lơ ở đầu danh sách OmniRoute mà không cuộn xuống đáy.
7. **Kỷ Luật Vận Hành Nạp Liên Tục Gối Đầu (Continuous Pipelined Runner Policy)**:
   - Khi user yêu cầu *"Làm liên tục luôn đi log cho xong luôn trừ khi lỗi lạ ms đc dừng"*:
     - Tự động chuẩn bị cặp ứng viên mốc vàng tiếp theo (đủ 2FA, S7 online, port sạch) ngay trong lúc mẻ hiện tại đang chạy.
     - Ngay khi mẻ hiện tại xong: chụp proof đáy bảng gửi user, đồng thời dispatch ngay mẻ tiếp theo mà không dừng lại hỏi han.
     - Chỉ dừng lại khi gặp Lỗi Lạ (Hard Checkpoint SMS không có nút "Thử cách khác", sập mạng farm toàn diện, đổi giao diện Google).
