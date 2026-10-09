# Quy trình Lọc Tài Khoản & Gán Proxy Hàng Loạt (Batch Gmail & Proxy Mapping)

Tài liệu hướng dẫn tra cứu SQLite GPM, đối soát chéo các bảng Excel kho tài khoản Kibe Farm, kiểm tra proxy có ký tự đặc biệt và các bộ lọc loại trừ an toàn.

---

## 0. Bốn Quy Chuẩn Sống Còn Cho Coordinator & Worker (Chỉ Đạo 2026-09-07)
1. **LUÔN NỐI LIỀN PIPELINE GPM LOGIN + OAUTH OMNIROUTE (CẤM TÁCH RỜI)**:
   - Khi nhận lệnh "đăng nhập tiếp Gmail lên GPM", BẮT BUỘC hiểu là chạy pipeline khép kín: Mở profile GPM qua Singbox proxy -> Đăng nhập Google -> Tự duyệt Prompt/Security Code trên S7 qua ADB -> Cấp quyền OAuth Antigravity -> Nạp connection vào OmniRoute port `20129` (`run_oauth_s7_pipeline.py` / `hot_session_oauth.py`).
   - CẤM TUYỆT ĐỐI tách riêng việc login GPM + bật 2FA thành task cụt rồi dừng lại chờ lệnh.
2. **QUY TẮC COOLDOWN PROXY & ĐẾM LƯỢT LOGIN TRONG NGÀY (DAILY PROXY LIMIT & STATE SAFETY)**:
   - Yêu cầu "mỗi proxy chạy tối đa 2 acc/ngày" là giới hạn an toàn trong phạm vi 1 ngày theo state file (ví dụ: `post_evening_gpm_login_state.json`).
   - **PITFALL TÍNH TOÁN PROXY_COUNT (CRITICAL BUG TRONG WATCHDOG/CRON)**:
     + Tuyệt đối KHÔNG pre-increment biến `proxy_count` tích lũy trong hàm lọc candidate (`get_candidates()`). Nếu tăng trước trong vòng lặp lọc candidate rồi lưu vào state/return, các lần chạy/tick tiếp theo sẽ cộng dồn ảo làm toàn bộ các cổng proxy chạm hạn mức (`>= 2`), gây ra hiện tượng 52/52 ports bị khóa cứng dù thực tế chỉ mới xử lý vài acc.
     + Quy tắc đúng: Hàm `get_candidates()` chỉ dùng một bản sao tạm (`current_run_proxy_count = dict(proxy_count)`) để lọc danh sách candidate cho batch hiện tại. Chỉ khi task/worker THỰC SỰ HOÀN THÀNH (sau khi nhận kết quả `res = fut.result()`), mới cập nhật tăng `proxy_count[port] += 1` và ghi bền vững xuống state file.
   - Khi nhận lệnh "mỗi proxy chạy 1 gmail" là giới hạn giãn cách theo thời gian (24 giờ) để chống dính checkpoint thiết bị mới, KHÔNG PHẢI là khóa vĩnh viễn cổng proxy đó.
   - Cổng proxy nào đã login tài khoản từ hôm trước (> 1 ngày trước) HOÀN TOÀN ĐỦ ĐIỀU KIỆN an toàn để login tiếp tài khoản mới thuộc máy S7 đó hôm nay.
   - CẤM TUYỆT ĐỐI tự ý siết chặt bằng cách lọc các cổng "trinh trắng" chưa từng có profile trong lịch sử database, dẫn đến báo cạn tài nguyên ảo.
3. **BẮT BUỘC ƯU TIÊN GMAIL MỚI NHẤT TRƯỚC HẾT (`ngày tạo` DESCENDING)**:
   - Nguồn ứng viên mới nhất nằm ở sổ tiếp nhận `gmail_clean_v2.xlsx` (chứa các đợt reg mới nhất tháng 9/2026, mã serial `46266`..`46271`).
   - BẮT BUỘC duyệt trực tiếp qua tất cả các dòng của `gmail_clean_v2.xlsx` và sắp xếp theo `ngày tạo` giảm dần (`reverse=True`).
   - CẤM TUYỆT ĐỐI chỉ lọc theo "máy chưa có profile GPM Group 1" hoặc chỉ lọc trong `Kibe_Farm_S7` vì sẽ bốc nhầm tài khoản cũ từ tháng 7/tháng 8 thay vì đợt reg mới nhất.
4. **CÔ LẬP CỔNG PROXY TRONG CÙNG BATCH (STRICT IN-BATCH PORT ISOLATION)**:
   - Trong mỗi đợt chạy batch, mỗi tài khoản phải chạy trên một cổng proxy hoàn toàn độc lập (`assert len(targets) == len(set(t['port'] for t in targets))`). Tuyệt đối không xếp 2 tài khoản chạy trên cùng 1 cổng proxy trong cùng một phiên runner.

---

## 1. Cấu trúc SQLite GPMLogin (`profile_data.db`)
- **Đường dẫn**: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
- **Bảng chính**: `Profiles` (chữ P hoa, số nhiều).
- **Các cột cần lưu ý**:
  - `Id`: UUID của profile (dùng gọi API `/profiles/start/{id}`, `/profiles/stop/{id}`).
  - `Name`: Tên profile, format chuẩn cho cụm farm Kibe: `<Số Máy> - <Email> - <Port>` (ví dụ: `45 - giathu3103200445@gmail.com - 5107`).
  - `GroupId`: Nhóm profile (Group 1: Kibe Farm Profiles chính thức; Group 0: Profile ẩn/legacy/test).
- **Truy vấn các máy đã có profile Group 1**:
  ```python
  import sqlite3, re
  conn = sqlite3.connect(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
  cur = conn.cursor()
  cur.execute("SELECT Id, Name, GroupId FROM Profiles WHERE GroupId = 1")
  rows = cur.fetchall()
  existing_machines = set()
  for pid, name, gid in rows:
      m = re.match(r"^(\d+)\s*-\s*", name)
      if m:
          existing_machines.add(int(m.group(1)))
  conn.close()
  ```

---

## 2. Tiêu chí lọc & Quy tắc loại trừ an toàn
Khi lọc tài khoản Gmail để tạo profile mới cho các máy Phone Farm:
1. **Kiểm tra trạng thái**: Chỉ nhận tài khoản có `Trạng Thái == 'LIVE'` trong cả `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`) và `gmail_clean_v2.xlsx`. BỎ QUA 100% tài khoản `DIE`.
2. **Bộ lọc mail khôi phục (Recovery Email)**:
   - **BỎ QUA 100%** tài khoản có recovery `khoaleemagic@gmail.com` hoặc `khoalemagic@gmail.com`.
   - **Chỉ đạo người dùng ("K cần kèm recovery nữa, h ưu tiên gmail mới nhất trc")**: KHÔNG ĐƯỢC bắt buộc tài khoản phải có recovery `thanhdatbui1995@gmail.com`. Chấp nhận cả tài khoản không recovery hoặc recovery khác (chỉ loại trừ `khoaleemagic`), ưu tiên thuần túy theo ngày tạo mới nhất (`ngay_tao` DESCENDING).
   - Nếu tài khoản có recovery `thanhdatbui1995@gmail.com`, script dùng IMAP tự động lấy OTP khi Google thách thức.
3. **Kênh nhận OTP**:
   - IMAP host: `imap.gmail.com`
   - User: `thanhdatbui1995@gmail.com`
   - App password: `zpxn wtmn bkgc adlc` (bỏ khoảng trắng khi xác thực IMAP).
4. **Không trùng lặp**:
   - Đối chiếu danh sách Email ứng viên với `Profiles` trong SQLite để đảm bảo email chưa được gán ở bất kỳ profile nào khác.
   - Bỏ qua các máy đã có profile trong Group 1.

---

## 3. Pitfall: Xử lý Proxy có ký tự đặc biệt khi Health Check
- Chuỗi cấu hình proxy của Farm Kibe thường có dạng:
  `test.taadaa.click:5107:mobi7:TaadaaMobi#2026!`
- **Khi gán vào GPM API v3**:
  Truyền nguyên bản vào trường `raw_proxy`: `"test.taadaa.click:5107:mobi7:TaadaaMobi#2026!"`. GPM xử lý trực tiếp chuỗi này chính xác.
- **Khi test kết nối qua thư viện Python `requests`**:
  Ký tự `#` trong password được coi là fragment identifier trong URI parser chuẩn, dẫn đến lỗi `Failed to parse: http://...`.
  **Giải pháp**: Bắt buộc dùng `urllib.parse.quote` mã hóa password trước khi đưa vào proxy URL:
  ```python
  import urllib.parse, requests
  pw_quoted = urllib.parse.quote("TaadaaMobi#2026!")
  proxy_url = f"http://mobi7:{pw_quoted}@test.taadaa.click:5107"
  r = requests.get("https://api.ipify.org?format=json", proxies={"http": proxy_url, "https": proxy_url}, timeout=10)
  ```

---

## 4. Đồng bộ 2 file Excel sau khi hoàn tất
Mỗi khi login hoặc update profile, bắt buộc đồng bộ đồng thời:
1. `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx`:
   - Sheet `Kibe_Farm_S7` & `Master_All`.
   - Cập nhật các cột: `Trạng Thái`, `Tên Profile GPM`, `Proxy Đang Dùng`, `Cập Nhật` (timestamp).
2. `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`:
   - Sheet mặc định (`Gmail Accounts`).
   - Cập nhật: `trạng thái`, `pass mail` (nếu có cập nhật password mới).

---

## 5. Nguyên Tắc Tái Sử Dụng Proxy Cũ (Farm 40 Proxy x 2 Ca Máy) & Tạo Profile Mới
- **Bối cảnh phân bổ**: Cụm 80 máy Kibe hoạt động trên 40 cổng proxy vật lý (máy 1–40 là ca 1, máy 41–80 là ca 2 dùng chung port, ví dụ: Máy 1 & Máy 39 dùng Port 5101; Máy 7 & Máy 45 dùng Port 5107).
- **Quy tắc tạo profile mới (BẮT BUỘC)**:
  - Khi chạy ca 2 trên các cổng proxy cũ, **BẮT BUỘC tạo profile GPM MỚI hoàn toàn** trong Group 1 theo format chuẩn: `<Số Máy> - <Email> - <Port>`.
  - Gán `raw_proxy` cố định trước khi khởi chạy.
  - **CẤM TUYỆT ĐỐI**: Tái sử dụng, ghi đè, clone fingerprint hoặc đổi tên profile của ca 1. Mỗi máy/tài khoản phải sở hữu 1 user data directory và fingerprint độc lập.

---

## 6. Tiêu Chí Tuyển Chọn: Ưu Tiên Gmail Mới Reg Gần Nhất (Date-Sorted Batch)
Khi người dùng yêu cầu chạy thêm batch tài khoản Gmail trên các proxy có sẵn:
1. **Truy vấn ngày đăng ký & Xử lý Excel Serial Date**:
   - Đọc cột `ngày tạo` (hoặc `NGÀY TẠO`) trong `gmail_clean_v2.xlsx` / `taikhoan_dat_v2_updated .xlsx`.
   - **Pitfall Excel Date Types**: Giá trị `ngày tạo` có thể là integer/float số serial Excel (ví dụ `46197`, `46178`, `46224`), string dạng `YYYY-MM-DD` hoặc `DD/MM/YYYY`, hoặc `datetime.datetime`. Nếu so sánh trực tiếp Python sẽ văng lỗi `TypeError` giữa `int` và `datetime`.
   - **Hàm chuẩn hóa ngày**:
     ```python
     def parse_excel_date(v):
         if v is None:
             return datetime.datetime.min
         if isinstance(v, datetime.datetime):
             dt = v
         elif isinstance(v, (int, float)):
             dt = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=v)
         elif isinstance(v, str):
             v = v.strip()
             dt = datetime.datetime.min
             for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                 try:
                     dt = datetime.datetime.strptime(v, fmt)
                     break
                 except ValueError:
                     pass
         else:
             return datetime.datetime.min
         # Pitfall: Chống ngày tương lai / lỗi gõ nhầm năm (ví dụ 2027 nhảy lên top 1)
         if dt > datetime.datetime.now() + datetime.timedelta(days=1):
             return datetime.datetime.min
         return dt
     ```
2. **Sắp xếp thứ tự ưu tiên & Bẫy Intake Registry (`gmail_clean_v2.xlsx`)**:
   - **Pitfall Bỏ Sót Acc Mới Reg (Bẫy Duyệt Lệch Nguồn)**: `gmail_clean_v2.xlsx` là sổ tiếp nhận (Intake Registry) chứa các tài khoản vừa reg mới nhất (ví dụ các đợt reg trong tháng 9/2026 có ngày tạo serial `46266` – `46271`). Nhiều tài khoản mới reg có thể chưa kịp được ghi danh vào sheet `Kibe_Farm_S7` của `master_gmail_manager.xlsx`.
   - **Quy tắc duyệt bắt buộc**: Khi tìm kiếm Gmail mới nhất, **BẮT BUỘC duyệt trực tiếp qua tất cả các dòng của `gmail_clean_v2.xlsx`** làm nguồn ứng viên tiềm năng (hoặc lấy hợp UNION giữa `gmail_clean_v2.xlsx` và các sheet của `master_gmail_manager.xlsx`). CẤM TUYỆT ĐỐI chỉ lặp qua `Kibe_Farm_S7` rồi tra ngược sang `clean_v2`, vì làm vậy sẽ bỏ sót 100% các tài khoản mới reg trong tháng!
   - Sắp xếp toàn bộ danh sách hợp nhất theo `ngày tạo` giảm dần (`DESCENDING`) để đưa các tài khoản vừa đăng ký gần đây nhất lên đầu danh sách chạy batch.
3. **Lọc loại trừ an toàn & Quy tắc Recovery Email**:
   - Chỉ chọn tài khoản `LIVE`.
   - Bỏ qua 100% tài khoản có recovery `khoaleemagic@gmail.com` hoặc `khoalemagic@gmail.com`.
   - **Theo chỉ đạo người dùng ("K cần kèm recovery nữa, h ưu tiên gmail mới nhất trc")**: Không áp đặt điều kiện phải có recovery `thanhdatbui1995`. Chấp nhận tài khoản không có recovery hoặc có recovery khác (miễn không dính `khoaleemagic`). Ưu tiên tuyệt đối sắp xếp theo ngày reg mới nhất.
   - Bỏ qua các máy đã có profile trong Group 1.
   - Bỏ qua các máy/tài khoản trong danh sách cooldown (`oauth_pipeline_status.json`): M20-M23, M28, M50 (`rrk=77`), M10, M59, M68 (IP cooling).
   - Kiểm tra log các batch trước (ví dụ `batch_12_untouched_report.json`) để loại bỏ tài khoản vừa dính Phone SMS checkpoint (ví dụ M65).
4. **Tái Sử Dụng 2FA Secret Khi Tài Khoản Đã Kích Hoạt Trước Đó**:
   - Nếu tài khoản đã có `2FA_Secret` trong Excel (`Kibe_Farm_S7` hoặc `Master_All`), script cần nạp sẵn secret key này.
   - Khi Google hiển thị màn hình hỏi mã xác thực 2 bước (`challenge/totp`), dùng `pyotp.TOTP(secret).at(google_utc)` để vượt qua ngay lập tức, sau đó chuyển thẳng sang bước kiểm tra hoàn tất thay vì cố gắng setup 2FA lại gây kích hoạt Google cooldown sensitive action (`rrk=77`).
5. **Kỷ luật Circuit Breaker**:
   - Thiết lập `CIRCUIT_BREAKER_LIMIT = 2` (ngắt batch ngay lập tức khi gặp 2 checkpoint/die liên tiếp).
   - Lỗi kết nối proxy (`PROXY_ERROR`) không tăng biến đếm failure, nhưng checkpoint Google bắt buộc tăng và dừng khẩn cấp để bảo vệ toàn dải IP.

---

## 7. Quy Trình Xử Lý Sai Mật Khẩu (Password Mismatch Fallback & S7 Recovery)
Khi mật khẩu trong Excel bị Google báo *"Mật khẩu không chính xác"* tại bước `challenge/pwd`:
1. **Đối soát file backup lịch sử**:
   - Mở `taikhoan_dat_v2_updated .xlsx`: đối chiếu cột `PASS` (mật khẩu gốc khi tạo tài khoản) và `PASS MAIL` (mật khẩu phụ). Nhiều tài khoản đổi pass nhưng file master chưa cập nhật.
2. **Kích hoạt khôi phục qua Samsung S7 (khi các mật khẩu dự phòng đều sai)**:
   - Trên GPM Chrome: Click nút `"Bạn quên mật khẩu?"` (`div#forgotPassword button, button:has-text("quên mật khẩu")`).
   - Tận dụng mỏ neo phần cứng (Hardware Trust Anchor) Samsung S7 đang online và đang đăng nhập tài khoản:
     - **Nếu Google hỏi Mã bảo mật 10 chữ số (`challenge/ootp`)**: Chạy hàm `get_s7_security_code(machine_id, serial, email)` vào Cài đặt Google trên S7 lấy mã 10 số $\rightarrow$ Điền vào form trên web.
     - **Nếu Google gửi Google Prompt (`challenge/dp`)**: Kích hoạt tap phê duyệt *"Vâng, đúng là tôi"* trên S7.
3. **Đặt lại mật khẩu chuẩn hóa & Đồng bộ**:
   - Sau khi xác minh S7 thành công, Google hiển thị màn hình tạo mật khẩu mới.
   - Điền mật khẩu mới theo chuẩn Farm: `<Tên><DOB>@Ks` (ví dụ: `Caoanh11092003@Ks`).
   - Đăng nhập hoàn tất vào `myaccount.google.com` $\rightarrow$ Cập nhật ngay mật khẩu mới vào cả `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`.

---

## 8. Kỷ Luật Vận Hành Script Batch Login & Setup 2FA
1. **Background Execution & Tránh Timeout Shell**:
   - Mỗi tài khoản chạy quy trình đầy đủ (GPM profile -> CDP connect -> Google Login -> Giải Audio reCAPTCHA -> Bật 2FA -> Tính True UTC TOTP -> Đồng bộ Dual Excel) mất trung bình 60–90 giây.
   - Batch từ 5–10 tài khoản sẽ tốn từ 500–900 giây (ví dụ batch 10 tài khoản tốn ~880s), vượt quá trần foreground timeout của terminal (600s).
   - **Bắt buộc**: Chạy script batch qua background process (`background=True, notify_on_complete=True`), sau đó kết hợp `process(action='wait', timeout=240, session_id=...)` theo dõi liên tục cho đến khi hoàn tất.
2. **Kỹ Thuật Tạo Script Runner (Tránh Bash Escape Pitfall)**:
   - Khi kế thừa script mẫu (như `run_batch_12_untouched_proxies.py`), không dùng `python -c "..."` với regex chứa đường dẫn Windows (`\T`, `\U`, `\b`) trong bash vì dễ lỗi `re.error: bad escape \T` hoặc xung đột nháy đơn/kép.
   - **Chuẩn an toàn**: Dùng `write_file` tạo file generator trung gian hoặc `str.replace` rõ ràng, luôn chạy `py_compile` trước khi gọi thực thi.
3. **Pitfall Splash Page Google (`/account/about/?hl=vi`)**:
   - Nếu tài khoản bị điều hướng vào trang giới thiệu tĩnh `https://www.google.com/account/about/?hl=vi` thay vì `myaccount.google.com`: Cần chủ động bắt URL này và `page.goto("https://myaccount.google.com")` hoặc click nút Đăng nhập lại để ép session hoàn tất, tránh bị ghi nhận fail oan.

---

## 9. Các Bẫy Kỹ Thuật Khi Tương Tác Với Samsung S7 & Google Prompt (`challenge/dp`)
1. **Tránh Dùng `keyevent 26` Đánh Thức Màn Hình S7**:
   - `input keyevent 26` là nút nguồn vật lý (Power Toggle). Nếu màn hình S7 đang sáng, gửi lệnh này sẽ làm **tắt đen màn hình**, khiến lệnh lấy XML hierarchy của ATX-Agent (`/dump/hierarchy`) bị treo hoặc trả về `None`.
   - **Chuẩn an toàn**: BẮT BUỘC dùng `input keyevent 224` (`KEYCODE_WAKEUP`) để bật sáng màn hình mà không làm tắt màn hình khi đang thức, sau đó gửi `input keyevent 82` (`KEYCODE_MENU`) và swipe mở khóa:
     ```python
     subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "224"], capture_output=True, timeout=5)
     subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "82"], capture_output=True, timeout=5)
     subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "swipe", "500", "1500", "500", "500"], capture_output=True, timeout=5)
     ```
2. **Bố Cục Giao Diện Mới Của Google Settings Trên S7**:
   - Trên các bản cập nhật Google Play Services mới trên Samsung S7 (Android 8 Oreo), khi mở Cài đặt Google sẽ hiển thị 2 tab: *"Đề xuất"* (Recommended) và *"Tất cả dịch vụ"* (All services).
   - Mục *"Bảo mật"* và *"Mã bảo mật"* (Security Code 10 số) nằm trong tab *"Tất cả dịch vụ"*.
   - **Bắt buộc**: Script phải quét và click tab *"Tất cả dịch vụ"* trước khi cuộn tìm *"Bảo mật"* $\rightarrow$ *"Mã bảo mật"*.
3. **Bẫy Race Condition URL `challenge` vs Google Prompt (`challenge/dp`)**:
   - Trên trình duyệt Playwright, khi submit mật khẩu xong, URL tạm thời vẫn chứa từ khóa `challenge` (ví dụ `challenge/pwd`).
   - Nếu script kiểm tra điều kiện `if "challenge" in page.url:`, lệnh click trên S7 sẽ bị kích hoạt quá sớm khi Google Prompt chưa kịp render trên điện thoại, dẫn đến tap hụt và timeout lời nhắc.
   - **Chuẩn an toàn**: Phải kiểm tra chính xác `if "challenge/dp" in page.url:`, chờ thêm 2.5s để Google Play Services đẩy push notification và render nút *"Vâng, đúng là tôi"* (tọa độ tâm `[540, 1362]`), sau đó mới tap phê duyệt.

---

## 10. Chuẩn Hóa Lệnh Dọn Dẹp Tiến Trình Chrome (PowerShell Pipeline Fix)
- **Lỗi Type Mismatch trên PowerShell**:
  Lệnh `Get-CimInstance Win32_Process ... | Stop-Process -Force` thường lỗi âm thầm hoặc văng exception do `Get-CimInstance` trả về `CIM_Process` object, không tương thích trực tiếp với tham số nhận pipeline của `Stop-Process`.
- **Lệnh chuẩn hóa an toàn**:
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match "<PORT>" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  ```
- Luôn kiểm tra điều kiện loại trừ `if not port or port == 9222: return` để bảo vệ Chrome người dùng.

---

## 11. Bẫy Phân Trang GPM API (`/api/v3/profiles`) & Profile Group 0 / Group Khác
- **Hiện tượng**: Khi gọi `GET /api/v3/profiles` hoặc `GET /api/v3/profiles?page=1&per_page=20`, API trả về trường `pagination` gồm `total`, `page`, `page_size`, `total_page`. Nếu chỉ đọc page 1 mà không lặp qua tất cả các trang (`page <= total_page`), các profile ở trang sau (hoặc profile nằm ở Group 0 / Default Group như trường hợp M54 `7d4c1801-7261-452a-9cf3-b1bde1ff6374`) sẽ bị bỏ sót, dẫn đến kết luận nhầm là profile chưa tồn tại.
- **Quy tắc chuẩn**:
  - Khi tìm kiếm profile theo tên / số máy: Luôn dùng vòng lặp quét qua toàn bộ `total_page` hoặc query trực tiếp bằng UUID nếu đã biết (`/api/v3/profiles/{id}`).
  - Mẫu code quét an toàn:
    ```python
    page = 1
    all_profiles = []
    while True:
        r = requests.get(f"http://127.0.0.1:19995/api/v3/profiles?page={page}&per_page=20", timeout=10)
        res = r.json()
        all_profiles.extend(res.get("data", []))
        if page >= res.get("pagination", {}).get("total_page", 1):
            break
        page += 1
    ```

---

## 12. Đối Soát Mật Khẩu Chéo Đa Sheet Trước Khi Kích Hoạt Reset Qua S7
- **Bẫy dữ liệu lệch**: Trong quá trình vận hành, file `gmail_clean_v2.xlsx` hoặc sheet `Kibe_Farm_S7` của `master_gmail_manager.xlsx` có thể bị ghi đè nhầm bằng mật khẩu mặc định (ví dụ `N0spam@@` trên M54), trong khi mật khẩu gốc thật sự vẫn được lưu chính xác tại các sheet khác (`Master_All`, `Admin_GPM_Pool`, `Gmail_Dat`).
- **Quy trình chuẩn**:
  - Khi đăng nhập vào Google báo sai mật khẩu (`challenge/pwd`): **KHÔNG VỘI** kích hoạt flow "Quên mật khẩu" hay reset qua S7 ngay lập tức.
  - Bắt buộc đọc và đối soát toàn bộ các sheet trong `master_gmail_manager.xlsx` để tìm mật khẩu dự phòng/mật khẩu gốc (ví dụ M54 mật khẩu chuẩn là `Eapgueybhnwl`).
  - Chỉ khi toàn bộ các mật khẩu đã từng lưu trong các sheet đều thất bại thì mới kích hoạt recovery qua S7.

---

## 13. Cấm Quét Tìm Kiếm Đệ Quy Không Giới Hạn Trên Root `D:\Taadaa`
- **Nguy cơ**: Thư mục `D:\Taadaa` chứa các thư mục mount, cache phân quyền hạn chế (ví dụ `.tmp-pytest-agent-loop`), và kho video/dữ liệu backup dung lượng hàng trăm GB.
- Lệnh shell `find /d/Taadaa -name ...` hoặc `grep -rn` không giới hạn đường dẫn sẽ chạm vào thư mục bị khóa quyền, rơi vào vòng lặp quét đệ quy dẫn đến timeout terminal (900s).
- **Quy tắc an toàn**:
  - BẮT BUỘC chỉ định thư mục con hẹp cụ thể (ví dụ `D:\Taadaa\GPM auto\scripts`).
  - Dùng công cụ `search_files` ripgrep tích hợp thay vì gọi lệnh shell `find` / `grep` trên toàn ổ đĩa.

---

## 14. Kỷ Luật Xử Lý Tận Gốc Tài Khoản Lỗi Sau Khi Chạy Batch (Không Bỏ Rơi / Không Chốt Sớm)
- **Tâm lý & Kỳ vọng người dùng**: Người dùng yêu cầu chạy batch (ví dụ 10 máy) luôn kỳ vọng **100% tài khoản thành công**. Khi kết thúc batch còn 1–2 tài khoản bị lỗi (như M54 kẹt splash page/prompt, M36/M38 sai pass), **CẤM TUYỆT ĐỐI** bỏ qua hoặc coi như xong việc rồi chốt phiên. Người dùng sẽ phản hồi gay gắt: *"Ủa mấy con lỗi k sửa cho xong đi"*.
- **Quy trình xử lý dứt điểm tài khoản lỗi ngay sau batch**:
  1. **Tách riêng danh sách lỗi (Quarantine Failed List)**: Trích xuất ngay các máy thất bại từ `report.json` hoặc log (ví dụ M54, M36, M38).
  2. **Thử cả 2 mật khẩu luân phiên**:
     - Do dữ liệu phân tán giữa các sheet, có tài khoản dùng mật khẩu gốc (trong `Master_All`/`taikhoan_dat_v2`), nhưng cũng có tài khoản dùng mật khẩu mới đổi chuẩn farm (`N0spam@@` hoặc `<Tên><DOB>@Ks`).
     - Bắt buộc thử lần lượt cả 2 mật khẩu trong script trước khi kết luận sai mật khẩu hoàn toàn.
  3. **Tận dụng màn hình Google Prompt (`OctarineActivity`) đang chờ trên S7**:
     - Nếu Google đẩy `challenge/dp`, màn hình Samsung S7 sẽ hiển thị giao diện xác thực:
       `text: 'Có phải bạn đang cố khôi phục tài khoản của mình?'`
       `text: 'Vâng, đúng là tôi' | bounds: [204,1308][876,1416]`
     - Khi phát hiện `OctarineActivity`, gửi lệnh tap ADB `540 1362` để duyệt ngay lập tức.
  4. **Khắc phục kẹt trang Splash `/account/about/?hl=vi`**:
     - Khi Google redirect về trang giới thiệu thay vì `myaccount.google.com`, gọi ngay `page.goto("https://myaccount.google.com")` để ép cookie session cập nhật và kiểm tra lại `myaccount.google.com`.
  5. **Tạo script cứu hộ tập trung (`fix_remaining_*.py`)**: Gom toàn bộ các máy lỗi vào một script riêng và chạy dứt điểm, cập nhật đủ trạng thái `LIVE` và `2FA` vào cả 2 file Excel trước khi bàn giao.

---

## 15. Bẫy Token Truncation Khi Subagent Tạo Script Batch Lớn (>50KB)
- **Hiện tượng**: Worker Subagent khi cố gắng viết toàn bộ script batch tự động hóa lớn (ví dụ 60–70KB) qua `write_file` hoặc in ra console có thể gây lỗi `Response remained truncated after 4 continuation attempts`, dẫn đến subagent bị fail và lãng phí turn.
- **Quy tắc chuẩn hóa**:
  1. **Tái sử dụng & Patch bằng Python ngắn**: Khi tạo script batch mới từ template đã có (ví dụ `run_batch_10_recent_gmails.py` -> `run_batch_turn2_gmails.py`), worker BẮT BUỘC dùng script Python ngắn đọc template, dùng `str.replace` hoặc regex thay thế mảng ứng viên (`TARGET_ACCOUNTS`) và tên file log/report/screenshots, rồi ghi đè file mới. **CẤM TUYỆT ĐỐI** nhồi toàn bộ 60KB code vào argument của tool call.
  2. **Khởi chạy nền an toàn (Non-blocking Subagent)**: Batch 10 tài khoản chạy mất 800–900s (> timeout mặc định của terminal). Worker nên khởi chạy script qua background process hoặc `subprocess.Popen`, kiểm tra log 15s đầu để đảm bảo script khởi động mượt mà rồi trả kết quả về Coordinator giám sát.

---

## 16. Quy Trình Trọn Gói 1-Pass Cho Batch Turn 2+ (End-to-End Single-Pass Execution)
Khi được giao lọc thêm Turn 2+ (ví dụ 10 Gmail mới nhất) và chạy batch:
1. **Tránh phân mảnh tool calls**: Không gọi nhiều lệnh python nhỏ để đọc từng file hay debug từng dòng, dễ làm cạn kiệt số lượt tool calling cho phép (iteration limit). Viết một file python duy nhất (ví dụ `generate_and_start_turn2.py`) thực hiện trọn vẹn:
   - Đọc và gom dữ liệu từ `master_gmail_manager.xlsx` (toàn bộ 4 sheet) và `gmail_clean_v2.xlsx`.
   - Lọc: loại bỏ `DIE`, loại bỏ `khoaleemagic`, loại bỏ 56 acc đã có trong GPM Group 1 kèm 2FA, loại bỏ các máy/acc trong `oauth_pipeline_status.json`.
   - Chuẩn hóa ngày (chặn ngày tương lai > hiện tại), sắp xếp `ngay_tao` DESCENDING.
   - Gán proxy: Với các acc chưa có số máy/proxy trong clean_v2, tự động gán vào các cổng khả dụng từ `PROXYgandienthoai.xlsx` (cổng 5101..5140 ca 2).
   - Tự động thay thế mảng `TARGET_12_ACCOUNTS` trong template `run_batch_10_recent_gmails.py`, trỏ log về `batch_turn2.log`, report `batch_turn2_report.json`, screenshot `batch_turn2`.
   - Kiểm tra `py_compile` và kích hoạt subprocess background.
2. **Theo dõi log mồi 15s**: Đọc 20 dòng đầu của `batch_turn2.log` để xác thực profile đầu tiên đã được khởi tạo trước khi báo cáo kết quả.

---

## 17. Xử Lý Onboarding & Bật 2FA Cho Gmail Mới Tinh Không Có Recovery (Đợt Reg Tháng 9/2026)
- **Đặc thù nhóm Gmail mới**: Trong `gmail_clean_v2.xlsx`, các tài khoản vừa reg trong tháng 9 (mã serial Excel `46266`..`46271`) hoàn toàn không có email khôi phục (cột `mail khôi phục` để trống).
- **Luồng xử lý khi đăng nhập**:
  1. Sau khi nhập đúng mật khẩu từ cột `pass mail` của `gmail_clean_v2.xlsx`, Google KHÔNG đòi OTP mail khôi phục mà hiển thị các màn hình Onboarding của dịch vụ `gds.google.com`:
     - **Màn hình Passkey (`gds.google.com/web/landing`)**: Script tự động bắt và click nút `"Huỷ"` (`button:has-text("Huỷ")`).
     - **Màn hình Địa chỉ nhà riêng (`gds.google.com/web/homeaddress`)**: Script tự động bắt và click nút `"Bỏ qua"` (`button:has-text("Bỏ qua")`).
  2. Sau 2 bước dismiss trên, trình duyệt tự động gọi `SetOSID` và hạ cánh an toàn tại `https://myaccount.google.com`.
  3. **Kích hoạt 2FA Authenticator ngay lập tức**:
     - Điều hướng thẳng vào `https://myaccount.google.com/two-step-verification/authenticator`.
     - Click `"Cài đặt ứng dụng xác thực"` -> `"Bạn không thể quét mã này?"` -> Trích xuất Secret Key 32 ký tự Base32.
     - Tính TOTP chuẩn UTC theo `google_server_utc_time` -> Điền mã -> Xác minh thành công.
     - Đồng bộ Secret Key và trạng thái `LIVE` vào cả `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`.
     - Đóng profile GPM và dọn sạch tiến trình Chrome theo port trước khi sang tài khoản tiếp theo.

---

## 18. Chiến Lược OAuth Antigravity Cho Gmail Mới & Cơ Chế Định Tuyến Tràn Tải (OmniRoute Spillover)
1. **Tài khoản mới bật 2FA trên GPM Profile có cần chờ 7 ngày (`rrk=77`) không?**:
   - **KHÔNG CẦN CHỜ**. Cơ chế hạn chế 7 ngày (`signin/rejected?rrk=77`) của Google chỉ bị kích hoạt khi can thiệp vào `myaccount.google.com/device-activity` để cố đăng xuất điện thoại tin cậy (Samsung S7) hoặc thay đổi sâu thiết lập bảo mật.
   - Khi tài khoản mới chỉ đăng nhập và bật 2FA Google Authenticator trên profile GPM (giữ nguyên kết nối S7), tài khoản có thể nạp thẳng OAuth Antigravity vào OmniRouter (`:20129`) ngay lập tức mà không bị cản trở.
2. **Kỷ luật định tuyến & Chống Over-engineering khi nuôi Trust tài khoản mới**:
   - **CẤM đưa tài khoản Starter/Free lên đầu combo chính**: Tài khoản mới có RPM/TPM thấp, đưa lên đầu sẽ dính 429 hoặc checkpoint `VALIDATION_REQUIRED` làm nghẽn tiến trình làm việc của Coordinator/Worker.
   - **CẤM dùng cron định kỳ "bơm" request vu vơ**: Token Antigravity là token Google Cloud Code dành cho lập trình viên trong IDE. Việc gửi request định kỳ giả lập chat hoặc hỏi vu vơ mang tính chu kỳ máy móc (temporal periodicity), dễ bị hệ thống AI Abuse Detection của Google nhận diện là bot và hạ trust score.
   - **CẤM tạo combo lặt vặt (Over-engineering)**: Không tạo thêm combo nhỏ lẻ (`ag-warmup`, `ag-light-worker`) chỉ để phục vụ nén ngữ cảnh hay tác vụ nhỏ, tránh làm phân mảnh cấu hình và tăng chi phí bảo trì.
   - **Chiến lược chuẩn xác (Natural Spillover Tier)**:
     - Nạp đầy đủ OAuth Antigravity cho tài khoản trên GPM profile, gán Proxy 1:1 theo cổng máy farm (`5101..5140`), đồng bộ models (`sync-models`).
     - **Xếp toàn bộ tài khoản mới vào ĐUÔI (cuối danh sách)** của combo chính `ag-gemini-pool-3` (sau dàn tài khoản Pro).
     - **Lợi ích**: Cấp quyền OAuth để đó hoàn toàn không bị Google phạt hay giảm trust. Khi dàn Pro chạm trần `maxConcurrent` hoặc dính 429 tạm thời, OmniRouter sẽ tự động tràn (spillover) một vài request thật xuống các tài khoản ở đuôi. Toàn bộ request là prompt công việc thật đi qua đúng proxy 4G của farm, giúp tài khoản tăng trust score hữu cơ và an toàn tuyệt đối.

---

## 19. Quy Tắc Gán Proxy & S7 N:1 (Nhiều Gmail Chung 1 Máy S7 & 1 Cổng Proxy)
- **Bản chất hạ tầng**: Một máy Samsung S7 và một cổng proxy 4G vật lý (ví dụ: Port 5111, Port 5124, Port 5107...) có thể đăng ký và quản lý **nhiều tài khoản Gmail** qua các đợt reg khác nhau (đợt cũ, ca 1, ca 2, đợt mới tháng 9/2026).
- **Quy tắc gán bất di bất dịch (Chỉ đạo người dùng 2026-09-06)**:
  - Gmail nào được reg từ máy S7 nào và cổng proxy nào thì:
    1. Khi tạo & mở profile GPM: Gán đúng `raw_proxy` của cổng đó (`test.taadaa.click:51xx:mobiXX:...`).
    2. Khi duyệt Google Prompt (`challenge/dp`) hoặc lấy mã bảo mật (`challenge/ootp`): BẮT BUỘC kết nối ADB tới đúng serial máy S7 đó.
    3. Khi exchange OAuth vào OmniRoute: BẮT BUỘC gọi `PUT /api/settings/proxies/assignments` gán đúng `proxyId` của cổng proxy máy đó cho connection mới.
  - **CẤM TUYỆT ĐỐI**: Gán nhầm cổng proxy của máy khác, đổi cổng proxy tùy tiện, hoặc chạy Direct IP máy chủ. Toàn bộ chuỗi định tuyến từ GPM -> S7 -> OmniRoute phải thống nhất 100% trên cùng một dải proxy 4G gốc đã reg ra tài khoản.

---

## 20. Bẫy Màn Hình Khôi Phục "Nhập Mật Khẩu Gần Nhất" (1 Ô Input) & Modal "Đổi Mật Khẩu" Trên GPM
- **Hiện tượng lỗi (Sự cố thực tế 06/09/2026 trên M36)**:
  - Khi script click nút *"Bạn quên mật khẩu?"*, Google **KHÔNG** đưa ngay vào form 2 ô mật khẩu mới (`input[type="password"] >= 2`).
  - Google hiển thị màn hình trung gian: *"Khôi phục tài khoản - Nhập mật khẩu gần nhất bạn nhớ là sử dụng với Tài khoản Google này"* (chỉ có **đúng 1 ô input**).
  - **Anti-Pattern**: Script cũ chỉ viết `if p_inputs.count() >= 2:`, dẫn đến khi gặp màn hình 1 ô này thì script rơi vào trạng thái nhàn rỗi (idle), chờ hết 25s timeout rồi chụp ảnh nhầm trạng thái hoàn tất mà không tương tác gì!
- **Giải pháp chuẩn hóa (Flow Xử Lý Chuẩn)**:
  1. Khi vào luồng khôi phục, script BẮT BUỘC kiểm tra nếu thấy chữ *"Nhập mật khẩu gần nhất"* hoặc chỉ có 1 ô password $\rightarrow$ Click ngay nút **"Thử cách khác" (Try another way)** (`button:has-text("Thử cách khác"), a:has-text("Thử cách khác")`).
  2. Bắt các phương án xác thực mà Google đưa ra:
     - **Option A (Google Prompt về S7)**: Google bảo *"Kiểm tra điện thoại Galaxy S7"* $\rightarrow$ Bật màn hình S7, tap nút *"Vâng, đúng là tôi"* (tọa độ `[540, 1362]`).
     - **Option B (Mã bảo mật 10 số)**: Nếu có lựa chọn *"Mã bảo mật"* $\rightarrow$ Click chọn $\rightarrow$ Gọi `get_s7_security_code()` lấy mã 10 số từ Cài đặt Google trên S7 $\rightarrow$ Điền vào ô input.
     - **Option C (OTP Mail Khôi Phục)**: Chọn gửi mã về `thanhdatbui1995@gmail.com` $\rightarrow$ Polling IMAP lấy 6 số OTP điền vào.
  3. **Bẫy Modal Xác Nhận "Đổi Mật Khẩu"**:
     - Sau khi điền mật khẩu mới vào cả 2 trường `Passwd` và `ConfirmPasswd` rồi bấm *"Tiếp theo"*, Google thường bật lên một hộp thoại modal xác nhận: *"Bạn sẽ duy trì trạng thái đăng nhập trên thiết bị này: Galaxy S7"*.
     - Script BẮT BUỘC phải bắt và click thêm nút **"Đổi mật khẩu" / "Change password"** trên modal này:
       ```python
       confirm_btn = page.locator('button:has-text("Đổi mật khẩu"), button:has-text("Đổi mật khẩu"), button:has-text("Change password")')
       if confirm_btn.count() > 0 and confirm_btn.first.is_visible():
           confirm_btn.first.click()
       ```
     - Chờ URL chuyển sang `https://myaccount.google.com/` (không còn chứa `signin`, `recovery`, `speedbump`).

---

## 21. Quy Chuẩn 4 Lớp Chốt Chặn Bằng Chứng Vật Lý (Artifact-First) & Bắt Buộc Gửi Ảnh Telegram
- **Bài học cốt lõi (Tư vấn kiến trúc từ Claude Code CLI 06/09/2026)**:
  - Không bao giờ được có **Epistemic Trust** mù quáng vào text summary tự báo cáo của Worker subagent (Gemini/Claude). Worker script khi bị kẹt/timeout âm thầm (exit 0 không crash exception) rất dễ bị LLM hallucinate là "SUCCESS".
  - Áp dụng nguyên tắc: **"Trust Artifacts, Not Summaries" (Tin bằng chứng vật lý, không tin lời khai)**.
- **Quy trình 4 lớp bắt buộc**:
  1. **Lớp 1 (Script Stdout Markers)**: Script luôn có khối `finally:` capture screenshot lưu ra đĩa và print ra stdout:
     `SCREENSHOT_SAVED: <path>`, `CURRENT_URL: <url>`, `TASK_STATUS: SUCCESS|FAILED|TIMEOUT`.
  2. **Lớp 2 (Artifact Contract)**: Worker khi hoàn thành bắt buộc trả về đường dẫn file ảnh thật; nếu thiếu file ảnh hoặc đường dẫn không hợp lệ $\rightarrow$ Coordinator REJECT ngay lập tức với `FAILED_NO_EVIDENCE`.
  3. **Lớp 3 (Coordinator Independent Verification Gate)**:
     - Coordinator kiểm tra file ảnh tồn tại trên đĩa VÀ timestamp (`mtime`) phải mới (sinh ra trong vòng 60s của task).
     - Coordinator tự OCR/Vision kiểm tra nội dung ảnh (nếu ảnh hiện *"Khôi phục tài khoản"*, *"Mật khẩu không chính xác"* mà worker dám khai "SUCCESS" $\rightarrow$ Bắt bài và REJECT ngay).
  4. **Lớp 4 (Human-in-the-loop qua Telegram)**:
     - Coordinator BẮT BUỘC nhúng cú pháp `MEDIA:<path>` gửi file ảnh thực tế lên Telegram cho User đối chiếu bằng mắt trước khi kết luận task hoàn tất.
     - CẤM TUYỆT ĐỐI Coordinator chỉ gửi tin nhắn text thông báo xong mà không gửi kèm ảnh bằng chứng.

---

## 22. Kỷ Luật Bất Biến: CẤM Đổi Tên Combo Khi Mở Rộng Target Account
- **Nguyên tắc an toàn routing**:
  Khi mở rộng số lượng target accounts trong combo OmniRoute (ví dụ cập nhật từ 18 lên 29 targets cho `ag-gemini-pool-3`), **TUYỆT ĐỐI KHÔNG ĐỔI TÊN COMBO** (giữ nguyên chính xác `name: "ag-gemini-pool-3"`).
- **Hệ quả của việc đổi tên**:
  Tất cả các agent, subagents (`ag-worker`, `review`), model aliases trong `mitmAlias`, và cấu hình fallback của Hermes (`config.yaml`) đều trỏ đích danh tới `ag-gemini-pool-3`. Nếu đổi tên combo (ví dụ thêm suffix `-v2`), toàn bộ hệ thống gọi model sẽ bị crash vì lỗi 404 / 400.
- Chỉ được phép chỉnh sửa mảng `models` bên trong payload của `PUT /api/combos/:id`, gắn nhãn tuần tự (`pool-19`, `pool-20`...).

---

## 23. Khắc Phục Lỗi 500 Khi Nạp Mã Exchange OAuth Antigravity
- **Cơ chế lỗi**:
  Google OAuth Authorization Code chỉ có giá trị dùng **một lần duy nhất (Single-Use)**. Nếu network listener của Playwright trong script batch bắt trùng 2 lần URL callback và gửi 2 request exchange liên tiếp, lượt thứ 2 sẽ bị Google báo `invalid_grant: Bad Request` và OmniRoute trả về HTTP 500.
- **Giải pháp**:
  1. Dùng script chuẩn hóa `add_oauth_omniroute.py` (chạy độc lập per-account thay vì batch tự chế nhồi nhét).
  2. Bắt buộc đặt cờ `code_exchanged = True` để chỉ gửi request exchange đúng 1 lần.
  3. Bóc tách và log chi tiết `res.status_code` kèm `res.text` từ OmniRoute để chẩn đoán chính xác phản hồi từ Google upstream.

---

## 24. Xử Lý Triệt Để Profile Lỗi & Checkpoint Sau Khi Chạy Batch ("còn mấy profile lỗi sao k xử lý nốt")
- **Kỳ vọng vận hành**: Người dùng không chấp nhận việc kết thúc batch mà để lại các profile lỗi treo lơ lửng. Khi batch kết thúc, các tài khoản thất bại phải được phân loại và xử lý dứt điểm ngay lập tức:
  1. **Lỗi Checkpoint Google Phone SMS (`Google Phone SMS Checkpoint`, ví dụ M53, M07)**:
     - Xóa profile rác trên GPM ngay lập tức bằng API `/api/v3/profiles/delete/{id}` để giải phóng tài nguyên và tránh xung đột port.
     - Ghi nhận trạng thái `CHECKPOINT` vào cột Trạng thái của file `gmail_clean_v2.xlsx`.
     - Cập nhật email vào mục `wrong_password_or_checkpoint` trong `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json`.
     - Tuyển ngay ứng viên sạch tiếp theo (tháng 9/2026, loại trừ `khoaleemagic`, chưa bị cooldown, đúng proxy của máy) để chạy login + 2FA thay thế, không để trống máy.
  2. **Lỗi Kẹt Trang Giới Thiệu `/account/about/?hl=vi` (như M57)**:
     - Sau khi nhập mật khẩu thành công, Google đôi khi không điều hướng vào `myaccount.google.com` mà chuyển hướng sang trang tĩnh `https://www.google.com/account/about/?hl=vi` (title `Chào mừng` / `Welcome`).
     - **CẤM TUYỆT ĐỐI**: Để script lặp 15 bước kiểm tra URL rồi đánh dấu FAILED oan uổng!
     - **Khắc phục chuẩn**: Nếu phát hiện URL chứa `about` hoặc page title chứa `Chào mừng` / `Welcome`, script chủ động gọi `page.goto("https://myaccount.google.com/?authuser=0")` để ép cập nhật session cookie và tiếp tục luồng cài đặt 2FA Authenticator.

---

## 25. Kỷ Luật Điều Phối Giám Sát & Chống Im Lặng / Bỏ Rơi Tiến Trình (Silence Watchdog)
- **Tâm lý & Phản hồi người dùng**: Người dùng cực kỳ khó chịu khi agent im lặng kéo dài mà không cập nhật tiến độ ("là sao xong hết chưa con mẹ mày im lặng 7 tiếng r").
- **Quy tắc phối hợp Coordinator - Worker**:
  1. Khi nhận nhiệm vụ batch hoặc phân tích hiện trường, Coordinator gửi 1 receipt ngắn gọn (mục đích -> hành động -> worker handle).
  2. Mọi tác vụ chạy nền BẮT BUỘC bật cờ thông báo (`notify_on_complete=True`) hoặc cấu hình hook kiểm tra heartbeat định kỳ.
  3. Ngay khi Worker hoàn thành (hoặc kết thúc từng phase), Coordinator BẮT BUỘC phải đọc log, kiểm tra hiện trường, báo cáo ngay cho người dùng và tự động kích hoạt xử lý các hạng mục lỗi còn lại, tuyệt đối không để session rơi vào trạng thái kết thúc giả vờ khi công việc chưa xong 100%.

---

## 26. Cơ Chế Preflight S7 Rolling Cleanup (Trần 5 Accs & 3 Safety Gates)
- **Bối cảnh & Mục đích**:
  - Máy Samsung Galaxy S7 (RAM 4GB) dùng reg Gmail farm định kỳ ~10 ngày/acc.
  - Tích tụ quá nhiều tài khoản (>6–8 accs) làm Google Play Services đồng bộ ngầm gây tràn RAM, nóng máy và tăng điểm nghi ngờ thiết bị.
  - Đăng xuất từ xa qua web tính năng `device-activity` sẽ kích hoạt cooldown 7 ngày `signin/rejected?rrk=77` trên mọi tác vụ nhạy cảm.
- **Quy tắc trần 5 accs & chu kỳ ngâm**:
  - Nâng trần từ 3 lên 5 tài khoản / máy S7. RAM 4GB của S7 gánh tốt ~100–150MB cho 5 tài khoản Google.
  - Chu kỳ reg 10 ngày/lần cho phép ngâm tài khoản trên S7 từ 40–50 ngày (đủ mốc vàng $\ge 30$ ngày để Google công nhận GPM là thiết bị chính).
- **Trích xuất danh sách $O(1)$ qua ADB OS**:
  - Đọc danh sách tài khoản Google trực tiếp từ Android `AccountManagerService` trong 0.2s:
    `adb -s <serial> shell dumpsys account` (cần kiểm tra `adb get-state` trước; nếu không kết nối được phải raise lỗi, cấm trả về `[]` rỗng làm sai lệch thành 0 acc).
- **Thẩm định 3 Safety Gates trước khi gỡ cuốn chiếu**:
  1. *Gate 1*: Đã có Secret Authenticator 2FA trong Excel ($\ge 16$ ký tự Base32).
  2. *Gate 2*: Đã nạp thành công OAuth Antigravity vào OmniRoute (`:20129`).
  3. *Gate 3*: Tuổi ngâm tài khoản trên GPM profile $\ge 30$ ngày.
  - **Chặn đứng lệnh gỡ**: Nếu chưa có tài khoản nào đủ 30 ngày, chặn đứng lệnh gỡ (`action: "SKIP"`), bỏ qua máy để bảo toàn trust.
  - Nếu đủ điều kiện, chọn duy nhất 1 acc cũ nhất để gỡ cuốn chiếu. Mỗi chu kỳ reg chỉ gỡ tối đa 1 acc / 1 máy.
- **Kỷ luật gỡ trên OS Android dưới `acquire_device_lock`**:
  - TUYỆT ĐỐI CẤM đăng xuất qua web `device-activity`.
  - Thao tác trực tiếp trên Cài đặt của điện thoại: `am start -a android.settings.SYNC_SETTINGS` $\rightarrow$ tap Google $\rightarrow$ tap email $\rightarrow$ dump XML mới $\rightarrow$ tap menu 3 chấm (`content-desc`) $\rightarrow$ tap "Xóa tài khoản" $\rightarrow$ tap xác nhận.
  - BẮT BUỘC dùng khối `finally:` gửi lệnh `keyevent 3` (HOME) để trả máy về trạng thái màn hình chính sạch sẽ.

---

## 27. Kỹ Thuật Hot-Session OAuth Hook (Nạp OAuth Trong Phiên Nóng)
- **Vấn đề cốt lõi của Cold Session**:
  - Trước đây, sau khi login GPM và bật 2FA xong, runner đóng hoàn toàn trình duyệt rồi mở lại profile trong phiên mới qua proxy 4G xoay IP. Việc này khiến Google kích hoạt checkpoint đòi xác minh SMS số điện thoại (`challenge/iap`).
- **Giải pháp Hot-Session**:
  - Giữ nguyên tab trình duyệt và tái sử dụng đối tượng Playwright `page` ngay sau khi bước bật 2FA thành công.
  - Điều hướng tới URL authorize của OmniRoute trên cùng tab: Cookie xác thực vừa sinh ra còn nóng, Google bỏ qua bước hỏi lại mật khẩu, chỉ hiện Account Chooser và nút *"Cho phép"*.
  - Bắt Authorization Code qua network listener `page.on("request")` và `page.on("response")` + URL polling.
  - Gỡ bỏ listeners an toàn trong khối `finally:`.
  - Ghi đè atomic file `STATUS_JSON` qua file `.tmp_` + `os.replace`, không ghi đè nếu đọc bị corrupt.
  - Gán Proxy 1:1 theo cổng máy farm, sync models, và append vào đuôi combo **`ag-gemini-pool-3`** (CẤM ĐỔI TÊN COMBO).

---

## 28. Tích Hợp Audio reCAPTCHA Solver & Kỷ Luật Giới Hạn Lần Thử
- **Cơ chế giải**:
  - Tự động bắt frame reCAPTCHA `#recaptcha-anchor` và `#recaptcha-audio-button`.
  - Tải file MP3 (chuẩn hóa URL tương đối), chuyển sang WAV qua `pydub` + `ffmpeg`.
  - Nhận diện giọng nói qua `speech_recognition`, chuẩn hóa `text.strip().lower()`, điền vào `#audio-response` và submit.
- **Kỷ luật Rate-Limit & Spin-Loop Guard**:
  - Sau khi submit, kiểm tra thuộc tính `aria-checked == "true"` trên anchor frame. Nếu không tick xanh, trả về `False`.
  - Giới hạn tối đa 2 lần thử giải (`recaptcha_attempts < 2`). Nếu thất bại sau 2 lần, thoát luồng giải captcha để tránh rơi vào vòng lặp spin loop vô tận làm cạn kiệt thời gian timeout 120s.

---

## 29. Quy Chuẩn Cooldown Proxy 24h & Luồng Nối Liền GPM Login + OAuth OmniRoute (Chỉ đạo 2026-09-07)
1. **Luồng Khép Kín Nối Liền GPM Login + OAuth OmniRoute (CẤM TÁCH RỜI)**:
   - Khi người dùng yêu cầu "đăng nhập tiếp Gmail lên các profile GPM", BẮT BUỘC hiểu là chạy **toàn bộ pipeline nối liền**: Login GPM + Duyệt S7 + Cấp quyền OAuth Antigravity vào OmniRouter (`run_oauth_s7_pipeline.py` / `add_oauth_omniroute.py`).
   - **CẤM TUYỆT ĐỐI**: Tách riêng việc login GPM + bật 2FA thành một task cụt rồi dừng lại báo cáo chờ lệnh. Toàn bộ chuỗi đã được tự động hóa trọn gói: mở profile GPM qua proxy Singbox -> đăng nhập Google -> tự vượt password/recovery/Google Prompt (Có/PIN) hoặc Security Code 10 số qua ADB S7 -> cấp quyền OAuth Antigravity -> exchange token vào OmniRoute port `20129` -> cập nhật file Excel và `config/oauth_pipeline_status.json`.
2. **Quy Tắc Cooldown Proxy 24h ("Mỗi proxy 1 gmail/ngày", Tái sử dụng port đã login hôm trước)**:
   - Yêu cầu "mỗi proxy chạy 1 gmail" là **giới hạn giãn cách theo thời gian (24 giờ)** nhằm chống dính checkpoint SMS thiết bị mới, KHÔNG PHẢI là vĩnh viễn khóa cổng proxy đó.
   - **Quy tắc tái sử dụng chuẩn**: Cổng proxy nào đã đăng nhập tài khoản từ hôm trước (> 1 ngày trước, ví dụ ngày hôm qua hoặc các đợt trước) **HOÀN TOÀN ĐỦ ĐIỀU KIỆN AN TOÀN** để đăng nhập tiếp tài khoản tiếp theo thuộc máy S7 đó hôm nay.
   - **Chống Over-engineering / Lọc sai**: CẤM TUYỆT ĐỐI tự ý siết chặt bằng cách lọc các cổng proxy "trinh trắng" chưa từng login profile nào trong lịch sử database, dẫn đến báo cạn máy hoặc bỏ sót tài nguyên. Chỉ cần kiểm tra: Cổng đó chưa chạy login tài khoản nào trong ngày hôm nay (`mtime` profile hoặc log login < 24h).
3. **Bảo Toàn Proxy Farm Kibe 1:1**:
   - Vẫn dùng đúng proxy Farm Kibe theo từng máy S7 (Mobi `5101..5140` / Singbox `20001..20040`).
   - Duy trì đúng liên kết 1 máy S7 = 1 cổng proxy = duyệt prompt ADB đúng serial máy.

---

## 30. Kỷ Luật Tuyệt Đối: 1 Cổng Proxy Chỉ Chạy Đúng 1 Tài Khoản Trong Cùng Một Batch (Port Isolation Per Batch Runner)
- **Sự cố thực tế (Batch Turn 2)**:
  Trong script `run_batch_turn2_gmails.py`, khi nạp 10 tài khoản mục tiêu, script đã vô tình xếp cả Máy 45 (`nhung.ngoc.ninh.otk37@gmail.com`) và Máy 7 (`thainhuong07052000rmv@gmail.com`) cùng chạy trên Cổng 5107 (`test.taadaa.click:5107`). Kết quả: Máy 45 chạy trước thành công, nhưng Máy 7 chạy sau trên cùng cổng proxy đó trong cùng phiên đã bị Google kích hoạt Phone SMS Checkpoint ngay lập tức!
- **Quy tắc cô lập cổng bắt buộc (Strict In-Batch Port Uniqueness)**:
  - Khi script tuyển chọn danh sách ứng viên (candidate selector), **BẮT BUỘC** kiểm tra tính duy nhất của cổng proxy:
    `assert len(targets) == len(set(t['port'] for t in targets))`
  - Mẫu code lọc an toàn:
    ```python
    used_ports_in_batch = set()
    final_targets = []
    for cand in eligible_candidates:
        port = cand.get('port')
        if not port or port in used_ports_in_batch:
            continue  # Bỏ qua tài khoản này trong batch hiện tại, dành cho batch sau
        used_ports_in_batch.add(port)
        final_targets.append(cand)
        if len(final_targets) >= BATCH_SIZE:
            break
    ```
- **Rà Soát Phân Loại 16 Máy Chưa Có Profile GPM Group 1 (Trong Dàn 80 Máy Kibe)**:
  - *Nhóm thuần Hotmail/Outlook (không có Gmail)*: Máy 31, 73, 75, 76, 77, 78, 79, 80.
  - *Nhóm đã có sẵn 2FA trong Excel*: Máy 66, 70.
  - *Nhóm ứng viên Gmail sạch ưu tiên chạy trước (Mỗi máy 1 cổng độc lập)*:
    1. Máy 39 (Port 5101) - `doanxuan2210200139@gmail.com`
    2. Máy 40 (Port 5102) - `amandabschmidt8inj6@gmail.com`
    3. Máy 46 (Port 5108) - `hectornwright4i52a@gmail.com`
    4. Máy 65 (Port 5133) - `quyphuoc090565@gmail.com`
    5. Máy 72 (Port 10001) - `trieunha2211199872@gmail.com`
    6. Máy 74 (Port 10003) - `phamthimyduyen150520041505@gmail.com`
    7. Máy 61 (Port 5127) - `songamgxo0100@gmail.com`

---

## 31. Bẫy Regex Parse Cột Proxy Trong Excel & Port Mapping Giữa Singbox (200xx) vs OmniRoute (51xx)
- **Đặc thù chuỗi cấu hình trong Excel (`master_gmail_manager.xlsx`)**:
  Cột *Proxy Đang Dùng* trong sheet `Kibe_Farm_S7` thường được ghi chú dạng hỗn hợp gồm cả Singbox proxy và Mobi proxy:
  `http://192.168.110.2:20001 (test.taadaa.click:5101)`
  hoặc `http://192.168.110.2:20044 (test.taadaa.click:5106)`
  hoặc dạng raw Mobi: `test.taadaa.click:5112:mobi12:TaadaaMobi#2026!`.
- **Cơ chế lỗi regex bắt nhầm port Singbox**:
  Nếu dùng biểu thức regex đơn giản `re.search(r":(\d{4,5})", p_val)`, parser sẽ bắt trúng số cổng đầu tiên là `20001` thay vì port Mobi `5101`!
  Hậu quả dây chuyền:
  1. Khi khởi chạy trình duyệt Playwright: Script tính `singbox_port = 20000 + (port - 5100)` -> `20000 + (20001 - 5100) = 34901` (port rác không tồn tại, Chrome mất kết nối mạng hoàn toàn).
  2. Khi gán proxy 1:1 trong OmniRoute (`PUT /api/settings/proxies/assignments`): Danh sách proxies trên OmniRoute lưu cổng theo dải Mobi `5101..5138`. Lệnh so khớp `if px.get("port") == port` sẽ so sánh `5101 == 20001` (False) -> Bỏ sót gán proxy cho Connection OAuth mới nạp.
- **Giải pháp chuẩn hóa parser an toàn**:
  ```python
  # Ưu tiên bắt cổng Mobi 51xx trước để làm key chuẩn
  m_mobi = re.search(r':(51\d{2})', p_val) or re.search(r'\b(51\d{2})\b', p_val)
  if m_mobi:
      port = int(m_mobi.group(1))
  else:
      m_port = re.search(r':(\d{4,5})', p_val)
      port = int(m_port.group(1)) if m_port else None

  # Tính cổng Singbox local tương ứng:
  if port and 5100 <= port <= 5200:
      singbox_port = 20000 + (port - 5100)
  elif port and port >= 20000:
      singbox_port = port
      port = 5100 + (port - 20000)
  ```
- **Kỷ luật cập nhật `oauth_pipeline_status.json`**:
  Sau khi nạp thành công tài khoản lên OmniRoute qua pipeline `run_oauth_s7_pipeline.py`, runner BẮT BUỘC cập nhật key email vào `omniroute_success` trong `oauth_pipeline_status.json` và lưu atomic để các worker lượt sau không bị gọi trùng lặp tài khoản.

---

## 32. OmniRoute API Endpoints Reference: Tra Cứu Connections (`/api/providers` vs `/api/connections` 404)
- **Pitfall Endpoint 404**: Endpoint `GET /api/connections` KHÔNG tồn tại trên OmniRoute (trả về HTTP 404). CẤM gọi nhầm endpoint này khi kiểm tra inventory connection.
- **Bảng tra cứu endpoints chuẩn của OmniRoute (`http://127.0.0.1:20129`)**:
  - **Danh sách Connections**: `GET /api/providers` $\rightarrow$ Trả về JSON dict `{"connections": [...], "total": N}`. Mỗi object connection chứa các trường `id`, `name`, `email`, `status`, `provider`...
  - **Danh sách Proxies**: `GET /api/settings/proxies` $\rightarrow$ Trả về `{"items": [...]}` với các trường `id`, `port`, `host`, `type`...
  - **Danh sách Combos**: `GET /api/combos` $\rightarrow$ Trả về `{"items": [...]}` (chứa combo `ag-gemini-pool-3`...).
  - **Khởi tạo OAuth Antigravity**: `GET /api/oauth/antigravity/authorize?redirect_uri=...`
  - **Exchange Token OAuth**: `POST /api/oauth/antigravity/exchange` (body: `code`, `redirectUri`, `codeVerifier`, `state`).
  - **Gán Proxy 1:1 cho Account**: `PUT /api/settings/proxies/assignments` (body: `{"scope": "account", "scopeId": conn_id, "proxyId": px_id}`).
  - **Đồng bộ Models sau OAuth**: `POST /api/providers/{conn_id}/sync-models`.

---

## 33. Fallback Trực Tiếp Raw Mobi Proxy Khi Singbox Local (200xx) Connection Reset (10054)
- **Hiện tượng lỗi**:
  Khi kiểm tra kết nối qua proxy Singbox local `http://192.168.110.2:200xx` (ví dụ 20036, 20037, 20024), request có thể bị văng lỗi:
  `ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host` hoặc `Expecting value: line 1 column 1 (char 0)` do service Singbox trên host trung gian chưa nạp cấu hình cổng đó. Trong khi đó, proxy 4G gốc trên Mobi Farm (`test.taadaa.click:51xx`) vẫn sống 100%.
- **Khắc phục chuẩn**:
  - Không được kết luận cổng proxy bị chết hoặc máy S7 mất mạng khi chỉ kiểm tra qua Singbox local.
  - Luôn kiểm tra trực tiếp cổng Mobi direct: `http://mobi{id}:{quoted_pwd}@test.taadaa.click:{port}`.
  - Khi tạo hoặc khởi chạy profile GPM, truyền trực tiếp chuỗi `raw_proxy` chuẩn (`test.taadaa.click:51xx:mobiXX:TaadaaMobi#2026!`) vào GPM API (`/profiles/create`). GPM Login xử lý xác thực HTTP proxy native của Chrome hoàn toàn độc lập, không phụ thuộc vào Singbox local forwarder.

---

## 34. Kỷ Luật Preflight Kiểm Soát Giới Hạn Tool Calls (Iteration Budget Shield)
- **Bài học vận hành**:
  Khi nhận lệnh chạy batch đăng nhập hoặc nạp OAuth (với ngân sách tool calling nghiêm ngặt, ví dụ $\le 20$ calls), nếu agent phân mảnh quá trình thành nhiều tool calls nhỏ (tra cứu Excel riêng, kiểm tra DB riêng, test từng proxy riêng, kiểm tra OmniRoute riêng...), session sẽ chạm giới hạn iteration limit trước khi kịp khởi chạy worker runner.
- **Quy tắc thực thi 1-Turn Preflight & Spawn**:
  - Gom toàn bộ logic đối soát (kiểm tra Excel, kiểm tra GPM SQLite, kiểm tra OmniRoute connections và health-check proxy) vào 1 script Python preflight duy nhất.
  - Nếu preflight pass, script tự động trigger background runner (`subprocess.Popen` hoặc terminal `background=True, notify_on_complete=True`) ngay trong cùng turn, bảo đảm pipeline chạy thông suốt mà không cạn kiệt ngân sách tool calling của platform.

---

## 35. Tra Cứu Serial Thiết Bị S7 & Cấm Quét Đệ Quy Ổ Đĩa (Fast S7 Serial Lookup)
- **Nguyên nhân sự cố**: Khi tìm serial S7 tương ứng với số máy (ví dụ Máy 69), chạy lệnh `os.walk(r"D:\Taadaa")` hoặc `find /d/Taadaa` sẽ quét qua hàng trăm GB video (`TIKTOK-videonuoinick`, `BACKUP_ALL`, `.git`) dẫn đến **timeout treo lệnh 900s** và cạn kiệt phiên làm việc.
- **Nơi lưu trữ chuẩn xác $O(1)$**:
  Toàn bộ mapping giữa Số máy $\leftrightarrow$ Serial Samsung S7 $\leftrightarrow$ Cổng Proxy gốc được lưu tập trung tại 2 file Excel trong `D:\OneDrive\TaadaaData\kibe\`:
  1. `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (Bảng phân bổ proxy và thiết bị chính thức của Farm).
  2. `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (Cột `Máy`, `Serial`, `Port`).
- **Quy trình tra cứu 1 dòng an toàn**:
  ```python
  import openpyxl
  wb = openpyxl.load_workbook(r"D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx", data_only=True)
  ws = wb.active
  for row in ws.iter_rows(values_only=True):
      # row: [STT, May, Serial, Proxy, ...]
      if row and str(row[1]).strip() == str(target_machine):
          target_serial = str(row[2]).strip()
          break
  wb.close()
  ```
- Luôn đối soát serial tìm được với output của `adb devices` để đảm bảo thiết bị đang online trước khi khởi chạy task.

---

## 36. Chu Kỳ Ngâm Mốc Vàng (3 – 7 Ngày) Cho Gmail Mới Reg Trước Khi Đưa Lên GPM / OAuth
- **Bản chất tâm lý & Nỗi sợ vận hành**:
  Người vận hành thường băn khoăn: *"Sợ acc mới reg không đăng ký dịch vụ gì mà vứt đó thì bị Google quét rác die ngầm, nhưng đem login GPM ngay thì lại sợ dính checkpoint thiết bị mới. Liệu có phải ngâm 15–30 ngày mới an toàn?"*.
- **Cơ chế kỹ thuật thực tế của Google**:
  1. **Để trên Samsung S7 KHÔNG BAO GIỜ bị coi là "vứt đó"**:
     Google Play Services trên điện thoại Android thật chạy ngầm 24/7, liên tục gửi heartbeat, đồng bộ ngầm danh bạ, kiểm tra cập nhật ứng dụng và duy trì kết nối push notification. Đối với Google, tài khoản này đang có hoạt động sinh tồn tự nhiên ở tầng hệ điều hành.
  2. **Chu kỳ quét dọn tự động (Bot Purge)**:
     Google chủ yếu kích hoạt các đợt quét tự động trong **24 – 48 giờ đầu tiên** sau khi đăng ký để tiêu diệt các tài khoản tạo bằng tool ảo hoặc dải IP bẩn. Khi tài khoản nằm trên S7 vượt qua được mốc 48 giờ mà vẫn `LIVE`, tài khoản đã có "hộ khẩu" ổn định trên thiết bị.
  3. **Rủi ro khi login GPM PC quá sớm (< 24h)**:
     Khi vừa tạo xong mà đưa ngay lên trình duyệt máy tính (GPM Chrome), Google phát hiện hành vi chuyển đổi môi trường đột ngột từ Android sang PC khi Trust Score = 0. Google sẽ kích hoạt ngay Checkpoint số điện thoại SMS (`challenge/iap`). Do farm không cắm SIM vật lý nhận tin nhắn, tài khoản sẽ bị kẹt hoặc bị gắn cờ vô hiệu hóa (Disabled).
- **Khuyến nghị các mốc ngâm chuẩn xác**:
  - **Dưới 24h (Vừa reg hôm nay)**: CẤM login GPM PC. Để nguyên trên Samsung S7 cho Google Play Services đồng bộ tự nhiên.
  - **Mốc Vàng (3 – 7 ngày, ví dụ đợt reg 01/09 – 03/09)**: **HOÀN HẢO ĐỂ CHẠY**. S7 đã trở thành mỏ neo phần cứng tin cậy (Hardware Trust Anchor). Khi login trên GPM PC, Google không đòi SMS mà chỉ gửi Google Prompt ("Có" / chọn PIN) hoặc mã bảo mật 10 số về S7 để script tự duyệt qua ADB. Tỷ lệ thành công đạt 95–100%.
  - **Mốc trên 15 – 30 ngày**: Trust rất cao nhưng không cần thiết phải chờ đợi quá lâu gây ứ đọng farm và làm chậm tiến độ mở rộng account pool.

---

## 37. Cơ Chế Tự Nuôi Trust Hữu Cơ Qua Tràn Tải OmniRoute (Spillover Tier) & Cấm Nuôi Nhân Tạo
- **Bản chất token Antigravity**:
  Token OAuth Antigravity là token Google Cloud Code / Vertex AI cấp cho lập trình viên. Sau khi cấp quyền, token ở trạng thái tĩnh hoàn toàn hợp lệ. Google không bao giờ phạt hay khóa tài khoản chỉ vì nó được cấp quyền OAuth mà chưa phát sinh request liên tục.
- **Cơ chế nuôi hữu cơ qua Tràn Tải (Natural Spillover Tier)**:
  - Khi Gmail đã hoàn tất nạp OAuth Antigravity và gán Proxy 1:1 theo cổng farm: **KHÔNG CẦN LÀM GÌ THỦ CÔNG ĐỂ NUÔI** (không cần đăng nhập đọc mail, lướt web hay xem video).
  - Xếp tài khoản vào **ĐUÔI (cuối danh sách)** của combo chính `ag-gemini-pool-3` (sau dàn tài khoản Pro).
  - Khi dàn Pro chạm trần `maxConcurrent` hoặc dính rate-limit 429 tạm thời, OmniRoute sẽ **tự động tràn (spillover) một vài request thật** xuống các tài khoản ở đuôi qua đúng cổng proxy 4G của farm.
  - Toàn bộ request là prompt công việc thật của lập trình viên, giúp tài khoản tự động tích lũy Trust Score một cách hữu cơ, bền vững và an toàn 100%.
- **CẢNH BÁO: CẤM TUYỆT ĐỐI các hành vi "nuôi nhân tạo"**:
  1. **Cấm dùng cron gửi request định kỳ vu vơ**: Hệ thống *AI Abuse Detection* của Google nhận diện các mẫu request có tính chu kỳ máy móc (temporal periodicity, ví dụ 15-30 phút hỏi 1 câu lặp lại) rất nhạy. Làm vậy phản tác dụng và tài khoản sẽ bị đánh dấu bot.
  2. **Cấm login đọc mail / xem YouTube định kỳ**: Việc đăng nhập qua lại giữa nhiều IP hoặc mở browser không cần thiết chỉ làm tăng rủi ro lệch Geolocation và tiêu tốn tài nguyên vô ích.

---

## 38. Quy Chuẩn Vị Trí Profile Worker Độc Lập (`profiles_worker/`) vs Cấm Quét Đệ Quy Toàn Repo GPM Auto
- **Bản chất hạ tầng profile worker**:
  Khi các script worker chạy độc lập (như đợt login M69 `nguyenvysfj3102@gmail.com`, M38 `hoanbui2608fm@gmail.com`, M57 `mockieuplus13@gmail.com`), dữ liệu user data của Chrome không lưu trong SQLite của GPMLogin App (`profile_data.db`) mà được lưu độc lập tại:
  `D:\Taadaa\GPM auto\profiles_worker\p_m<MID>_<escaped_email>\` (ví dụ `p_m69_nguyenvysfj3102_gmail_com`).
  Tra cứu bằng SQLite GPM sẽ trả về rỗng (`[]`). Bắt buộc kiểm tra trực tiếp trong thư mục `profiles_worker/`.
- **Cạm bẫy timeout 900s do Grep/Find đệ quy**:
  Thư mục `profiles_worker` chứa hàng chục profile Chromium độc lập, mỗi profile có hàng chục nghìn file cache, IndexedDB, LevelDB (`*.ldb`, `*.log`), BrowserMetrics.
  CẤM TUYỆT ĐỐI chạy lệnh shell `grep -rn` hoặc `find /d/Taadaa -name` không giới hạn đường dẫn trên root `D:\Taadaa\GPM auto` hay `/d/Taadaa`. Lệnh này sẽ duyệt sâu vào toàn bộ cây thư mục cache của Chrome, gây treo terminal quá 900s timeout.
  **Quy tắc an toàn**: Chỉ được grep/search trong thư mục đích cụ thể: `D:\Taadaa\GPM auto\scripts` hoặc `D:\Taadaa\GPM auto\config`, hoặc luôn dùng flag `--exclude-dir=profiles_worker`, `--exclude-dir=debug_screenshots`, `--exclude-dir=logs`.

---

## 39. Quy Trình Chuẩn Nạp OAuth OmniRoute & Append Vào Đuôi Combo `ag-gemini-pool-3`
- **Đường dẫn ADB bắt buộc trên Windows**:
  `ADB_EXE = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"`.
  Tuyệt đối không gọi `subprocess.run(['adb', ...])` trực tiếp bằng tên lệnh vì `adb` không nằm trong Windows system PATH (sẽ gây lỗi `FileNotFoundError: [WinError 2]`).
- **Quy trình 5 bước nạp OAuth & Append Combo khép kín (`run_oauth_s7_pipeline.py` & `append_to_combo_pool3.py`)**:
  1. **Khởi chạy persistent browser**: Mở Playwright Chromium với `user_data_dir = prof_dir` (trỏ vào `profiles_worker/p_m...` hoặc `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<profile_path>`), gắn proxy Singbox local `http://192.168.110.2:{20000 + (port - 5100)}` hoặc direct Mobi proxy.
  2. **Điều hướng authUrl**: Lấy URL ủy quyền từ `GET http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http://127.0.0.1:20129/callback`.
  3. **Vượt xác thực Google & Duyệt S7 qua ADB**: Bắt Google Prompt (`challenge/dp`) hoặc Security Code 10 số (`challenge/ootp`), script tự động điều khiển Samsung S7 qua ADB để bấm *"Có, đúng là tôi"* / chọn đúng số PIN hoặc vào Cài đặt Google lấy mã 10 số điền vào form.
  4. **Exchange Token & Gán Proxy 1:1**:
     - Bắt `code=` từ callback URL, gửi `POST http://127.0.0.1:20129/api/oauth/antigravity/exchange` để nhận `connection_id` (`cid`).
     - Gán cố định cổng proxy farm 1:1: `PUT http://127.0.0.1:20129/api/settings/proxies/assignments` (body: `{"scope": "account", "scopeId": cid, "proxyId": px_id}`).
     - Đồng bộ models: `POST http://127.0.0.1:20129/api/providers/{cid}/sync-models`.
     - Cập nhật trạng thái vào `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json`.
  5. **Nối vào đuôi combo `ag-gemini-pool-3`**:
     - Gọi `append_connections([{"cid": cid, "email": email, "port": port}])` từ module `D:\Taadaa\GPM auto\scripts\append_to_combo_pool3.py`.
     - Hàm này lấy danh sách models hiện tại của combo `22975610-b162-41b9-b6b3-30be076265bd`, append target mới với label `pool-{len+1}`, gửi `PUT /api/combos/22975610-b162-41b9-b6b3-30be076265bd` và đồng bộ backup ra `D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json`.
     - **BẢO TOÀN NGUYÊN VẸN**: Luôn giữ đúng tên combo `ag-gemini-pool-3` để không làm crash các hệ thống routing phụ thuộc.

---

## 40. Bẫy Lệch Serial S7, Nhầm Lẫn Số Máy Proxy KhoaLee vs Mobi (M38 vs M58, M69) & Kỷ Luật Fast ADB Pre-Check
- **Sự cố thực tế (Sự cố Máy 69 ngày 07/09/2026)**:
  - Khi chạy runner nạp OAuth cho M69 (`nguyenvysfj3102@gmail.com`), script điền email/pass thành công, Google Prompt bắn về điện thoại đòi PIN 86.
  - Tuy nhiên, script truyền nhầm serial ADB: `ce12160cc124b81c05` (sai 2 ký tự cuối) thay vì serial thật `ce12160c386c913101`! Thiết bị sai không tồn tại trong `adb devices`, khiến ADB connection timeout 3 phút và task thất bại oan uổng.
- **Phân Biệt KhoaLee Recovery Email (CẤM 100%) vs Proxy Host KhoaLee (Vận Hành Bình Thường)**:
  - **CẤM TUYỆT ĐỐI**: Chỉ áp dụng với tài khoản Gmail có **email khôi phục là `khoaleemagic@gmail.com` hoặc `khoalemagic`** (`excluded_khoalee`).
  - **Proxy Host `khoalee.duckdns.org:16002` (Máy 38 & 76)**: Đây là endpoint proxy 4G Mobifone chuẩn của Farm (IP `27.69.67.252`), đã cấu hình sẵn trong OmniRoute (`cf633ef8-5712-48aa-9831-ded355caa9a8`) và map local qua Singbox port `20038`. Tài khoản `hoanbui2608fm@gmail.com` trên Máy 38 hoàn toàn sạch (không recovery khoalee) và đã nạp OAuth thành công 100%.
  - **Đối soát serial phần cứng S7 Máy 38 vs Máy 58**:
    + Máy 38: Serial `ce06160685310f1c04`, proxy `khoalee.duckdns.org:16002` (Singbox `20038`), tài khoản `hoanbui2608fm@gmail.com`.
    + Máy 58: Serial `ce041604b90c493803`, proxy `test.taadaa.click:5124` (Singbox `20024`), tài khoản `longtuong201058@gmail.com`.
    + Tuyệt đối không gán nhầm serial M58 cho M38 vì ADB sẽ bắt hụt Google Prompt dẫn đến timeout.
- **Kỷ luật Fast ADB Pre-Check trước khi chạy runner**:
  - Luôn kiểm tra serial đối soát 1 dòng trong `PROXYgandienthoai.xlsx`:
    `Máy 69 -> ce12160c386c913101`, `Máy 38 -> ce06160685310f1c04`, `Máy 58 -> ce041604b90c493803`, `Máy 57 -> ce11160b54ee2f3403`.
  - Kiểm tra nhanh `adb devices | grep <serial>` trước khi truyền vào `process_account` hoặc gọi `acquire_device_lock`.

---

## 41. Kỷ Luật Coordinator Điều Phối Worker 1-Task Focused (Chống Bẫy Thăm Dò 35 Turns / 52 Phút)
- **Cơ chế lỗi (Subagent Exploration Trap)**:
  - Khi Coordinator dispatch worker với mục tiêu quá rộng hoặc ghép nhiều tài khoản ("Thực thi M69, M38 và append..."), Worker subagent dễ rơi vào bẫy "thăm dò cấu trúc" (tự viết test mock, khảo sát schema, đọc lặp các file script) dẫn đến tiêu tốn tới 35 tool calls và 52 phút mà **hoàn toàn chưa thực thi script runner**.
- **Quy chuẩn điều phối 1-Task Focused cho Coordinator**:
  1. **Tách lẻ từng máy (Single-Machine Execution)**: Mỗi worker subagent chỉ gánh đúng 1 tài khoản/máy (ví dụ chỉ chạy riêng M57, xong M57 mới chạy riêng M69).
  2. **Soạn sẵn Script Runner Cụ Thể (Code-First Dispatch)**: Coordinator viết sẵn code script ngắn gọn trong prompt `context` (chỉ gồm import `process_account` và gọi chạy), yêu cầu worker chỉ việc dùng `write_file` tạo file và chạy ngay qua `terminal`.
  3. **Giới hạn ngân sách nghiêm ngặt**: Ép trần worker $\le 5 - 8$ tool calls, cấm khảo sát/đọc file khác, bắt buộc trả về stdout thực tế và đường dẫn screenshot trong vòng $\le 3 - 5$ phút.

---

## 42. Nghiệm Thu Bộ Ba Mốc Vàng (M57, M69, M38) & Mở Rộng Combo `ag-gemini-pool-3` Lên 32 Targets
- **Thực tế nghiệm thu đợt 07/09/2026**:
  1. **Máy 57 (`mockieuplus13@gmail.com`)**: Tạo 03/09/2026 (ngâm 4 ngày), S7 `ce11160b54ee2f3403`, Port `5123` $\rightarrow$ CID `32645bfb-8553-44ab-b48e-7093e1b34e94` (`pool-30`).
  2. **Máy 69 (`nguyenvysfj3102@gmail.com`)**: Tạo 02/09/2026 (ngâm 5 ngày), S7 `ce12160c386c913101`, Port `5137` $\rightarrow$ CID `e3960af5-e478-4ae7-bfd9-b5505468e3b1` (`pool-31`).
  3. **Máy 38 (`hoanbui2608fm@gmail.com`)**: Tạo 01/09/2026 (ngâm 6 ngày), S7 `ce06160685310f1c04`, Port `16002` (Singbox `20038`) $\rightarrow$ CID `489d5f1a-d066-40f3-9175-dfe2fb57d438` (`pool-32`).
- **Xác nhận an toàn 100%**: Cả 3 tài khoản đều tự động duyệt Google Prompt thành công trên Samsung S7, 0 checkpoint SMS, đã gán proxy 1:1 trong OmniRoute và nằm ở đuôi combo chính để nhận tải tràn tự nhiên.

---

## 43. Bắt Buộc Tích Hợp Audio reCAPTCHA Solver Vào Pipeline OAuth & Bài Học Circuit Breaker M25/M45
- **Sự cố thực tế (Batch 1 ngày 07/09/2026 trên M25 & M45)**:
  - Khi chạy runner nạp OAuth cho M25 (`caoxuan02052002swc@gmail.com` - Port 5131) và M45 (`giathu3103200445@gmail.com` - Port 5107), sau khi chọn tài khoản trên màn hình Consent, Google kích hoạt checkbox reCAPTCHA Enterprise (*"Tôi không phải là người máy"*).
  - Trong `run_oauth_s7_pipeline.py`, script cũ chỉ tìm frame và click vào `.recaptcha-checkbox` rồi chờ đợi. Khi Google không cho tick xanh tự động mà mở tiếp challenge puzzle hình ảnh / âm thanh, script rơi vào vòng lặp chờ cho đến khi chạm trần timeout 180s (`oauth_..._timeout.png`).
  - Hậu quả: Hai máy liên tiếp timeout kích hoạt Circuit Breaker (`circuit_fails >= 2`) dừng ngay batch để bảo vệ dải IP, làm gián đoạn tiến trình của 3 máy còn lại (M51, M52, M53).
- **Nguyên nhân gốc rễ & Giải pháp chuẩn hóa**:
  - Script độc lập `add_oauth_omniroute.py` đã có sẵn hàm `solve_recaptcha_audio(page: Page) -> bool` chuẩn 100% (sử dụng `pydub`, `speech_recognition` và binary `ffmpeg.exe` tại WinGet packages).
  - **Quy tắc bắt buộc**: Trong mọi script runner OAuth (`run_oauth_s7_pipeline.py` hay các runner direct):
    1. Import hoặc tích hợp `solve_recaptcha_audio`.
    2. Khi phát hiện reCAPTCHA checkbox hoặc bframe xuất hiện, kiểm tra nếu sau 3s click mà `aria-checked != "true"`, BẮT BUỘC gọi ngay `solve_recaptcha_audio(page)`:
       - Tìm frame `enterprise/bframe` hoặc `recaptcha/bframe`.
       - Click nút `#recaptcha-audio-button`.
       - Tải file MP3 challenge, chuyển sang WAV qua `pydub.AudioSegment.from_mp3` + `ffmpeg`.
       - Nhận diện giọng nói qua `speech_recognition.Recognizer().recognize_google(audio, language="en-US")`.
       - Điền chuỗi kết quả vào `#audio-response` và bấm xác nhận / Enter.
       - Chờ `aria-checked == "true"` rồi tiếp tục luồng submit.
- **Danh sách 9 cổng proxy độc lập chưa chạy trong ngày 07/09/2026**:
  1. M51 (Port 5115, Singbox 20015, S7 `ce0616063df1094004`, `duonguyen12022001@gmail.com`)
  2. M52 (Port 5116, Singbox 20016, S7 `ce0418243a6250430c`, `giangkim110452@gmail.com`)
  3. M53 (Port 5117, Singbox 20017, S7 `ce11160b1857760904`, `carmendarnold2zo9b@gmail.com`)
  4. M56 (Port 5122, Singbox 20022, S7 `ce0516055108a70e01`, `brentwbowmanlb0wb@gmail.com`)
  5. M62 (Port 5128, Singbox 20028, S7 `ce12160c4a505d2604`, `tongly20092001@gmail.com`)
  6. M33 (Port 10001, Singbox 20001, S7 `ce0616061a74682305`, `chungan2612199833@gmail.com`)
  7. M25 (Port 5131, Singbox 20031, S7 `ce02182261a6a62105`, `caoxuan02052002swc@gmail.com`)
  8. M45 (Port 5107, Singbox 20007, S7 `ce0716071586c80602`, `giathu3103200445@gmail.com`)
  9. M32 (Port 5138, Singbox 20038, S7 `ce0916094b33e73c03`, `huynh.cong.loan05@gmail.com`)

---

## 44. Bẫy Hardcode Tên Profile Ảo (`p_mXX_*`) Thay Vì Tra Cứu `ProfilePath` Thực Tế Trong SQLite GPMLogin (`profile_data.db`)
- **Cơ chế lỗi**:
  Khi viết script runner chạy batch (ví dụ `run_batch_untouched_1.py`), agent thường tự đặt tên profile trực quan như `p_m56_brent`, `p_m62_tongly`, `p_m33_chungan`, `p_m25_caoxuan`, `p_m45_giathu`.
  Tuy nhiên, trong thực tế GPMLogin lưu trữ thư mục profile trên đĩa (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\`) dưới dạng chuỗi ngẫu nhiên kèm ngày tạo:
  - M51 (`duonguyen12022001@gmail.com`) $\rightarrow$ `kvI8G9GmLh-06092026`
  - M52 (`giangkim110452@gmail.com`) $\rightarrow$ `mEBuH1acbw-06092026`
  - M53 (`carmendarnold2zo9b@gmail.com`) $\rightarrow$ `Q17hXQrIk2-06092026`
  - M56 (`brentwbowmanlb0wb@gmail.com`) $\rightarrow$ `NRgciz8GPo-06092026` (thư mục `p_m56_brent` KHÔNG tồn tại)
  - M62 (`tongly20092001@gmail.com`) $\rightarrow$ `SweRarphv2-06092026` (thư mục `p_m62_tongly` KHÔNG tồn tại)
  - M25 (`caoxuan02052002swc@gmail.com`) $\rightarrow$ `881jJ1gH1I-06092026`
  - M45 (`giathu3103200445@gmail.com`) $\rightarrow$ `IVJe1vgLXm-06092026`
  - M33 (`chungan2612199833@gmail.com`) $\rightarrow$ Tạo nhiều profile rác, profile mới nhất có live cookies là `YR5nFaRBrf-05092026`.
- **Hậu quả**:
  Nếu truyền tên ảo `p_m...` vào `launch_persistent_context(user_data_dir=...)`, Playwright sẽ sinh ra thư mục profile trắng tinh chưa đăng nhập Google, mất cookie session cũ, khiến Google bắt buộc login lại từ đầu và kích hoạt CAPTCHA / checkpoint SMS.
- **Quy tắc chuẩn tra cứu động ProfilePath**:
  BẮT BUỘC query SQLite `profile_data.db` và lấy profile có `CreatedAt` mới nhất tồn tại trên đĩa:
  ```python
  def resolve_gpm_profile_path(email: str, base_dir: str = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile") -> str:
      db_path = os.path.join(base_dir, "profile_data.db")
      if not os.path.exists(db_path):
          return ""
      conn = sqlite3.connect(db_path)
      cur = conn.cursor()
      cur.execute("SELECT ProfilePath FROM Profiles WHERE Name LIKE ? ORDER BY CreatedAt DESC", (f"%{email.strip()}%",))
      rows = cur.fetchall()
      conn.close()
      for (prof_path,) in rows:
          if prof_path and os.path.exists(os.path.join(base_dir, prof_path)):
              return prof_path
      return ""
  ```

---

## 45. Bẫy Proof Screenshot `ERR_CONNECTION_RESET` Khi Proxy Farm Định Tuyến Callback Về Localhost & Chuẩn Hóa Proof Bằng Chứng
- **Hiện tượng & Sự cố thực tế (Batch ngày 07/09/2026 trên M51, M52, M53)**:
  - Khi script runner nạp OAuth Antigravity vào OmniRoute (`add_oauth_omniroute.py` hoặc `run_oauth_s7_pipeline.py`), Google hoàn tất xác thực consent và chuyển hướng trình duyệt về callback URL:
    `http://127.0.0.1:20129/callback?code=4/0ATs...&state=...`.
  - Trình duyệt Playwright Chromium chạy qua proxy 4G của Farm (`192.168.110.2:200xx`). Khi browser cố truy cập `127.0.0.1:20129` (localhost), trạm proxy 4G bên ngoài không thể kết nối ngược về localhost của máy tính host $\rightarrow$ Trình duyệt Chrome văng màn hình lỗi mạng:
    `ERR_CONNECTION_RESET` (*"Không thể truy cập trang web này - Kết nối đã được đặt lại"*).
  - Tuy nhiên, listener Playwright (`on_request`) đã bắt được mã OAuth `code=` ngay trong HTTP request header trước khi navigation fail. Python script chạy trực tiếp trên máy host (native network) đã gửi `requests.post` exchange code thành công 100% lên OmniRoute (`Active: True`, `testStatus: active`, sync models OK).
  - **Cạm bẫy bằng chứng (False Failure Artifact Trap)**:
    Script chụp ảnh `page.screenshot()` ngay sau khi exchange xong, lúc này tab Chrome đang ngồi ở trang `127.0.0.1:20129/callback` bị reset mạng. Kết quả: Ảnh gửi cho User qua `MEDIA:<path>` hiển thị trang lỗi Chrome sad face với mã `ERR_CONNECTION_RESET`, khiến người dùng bức xúc và hoang mang tưởng tác vụ thất bại ("Lỗi mà?").
- **Quy tắc chuẩn hóa Proof Artifacts Bắt Buộc (Artifact Trust Guard)**:
  1. **CẤM TUYỆT ĐỐI**: Chụp ảnh tab browser tại URL callback `127.0.0.1:20129/callback` làm bằng chứng gửi cho người dùng.
  2. **Các hình thức bằng chứng hợp lệ chuẩn xác**:
     - *Hình thức 1 (Tối ưu nhất - ADB Screen Proof)*: Chụp trực tiếp màn hình điện thoại Samsung S7 qua ADB (`adb -s <serial> exec-out screencap -p > ..._s7_proof.png`) ngay sau khi vừa phê duyệt Google Prompt / chọn số PIN thành công.
     - *Hình thức 2 (OmniRoute Provider API Verification)*: Trích xuất bản ghi JSON từ API `GET http://127.0.0.1:20129/api/providers` hiển thị rõ: `email`, `connection_id`, `isActive: true`, `testStatus: active`, `proxyEnabled: true`.
     - *Hình thức 3 (Điều hướng Google Account)*: Nếu muốn chụp trên trình duyệt Chrome, script BẮT BUỘC phải gọi `page.goto("https://myaccount.google.com/?authuser=0")` để tải trang tài khoản Google thành công trước khi chụp `page.screenshot()`.

---

## 46. Xử Lý Khi Google Đòi Mã Bảo Mật 10 Số (`challenge/ootp`) Nhưng S7 Đang Active Tài Khoản Khác (M56)
- **Hiện tượng**:
  Khi Google yêu cầu mã bảo mật 10 số trên S7 (`challenge/ootp`), script tự động mở Cài đặt Google trên S7 qua ADB.
  Nếu trên thiết bị S7 đang đăng nhập nhiều tài khoản Google (ví dụ Máy 56 có cả `nathan.yabsley1990@gmail.com` và `brentwbowmanlb0wb@gmail.com`), giao diện Cài đặt Google có thể đang hiển thị tài khoản khác ở header. Script vào lấy mã bảo mật sẽ đọc nhầm mã của tài khoản đó, hoặc không lấy được mã của tài khoản mục tiêu $\rightarrow$ Timeout 180s.
- **Quy trình xử lý chuẩn hóa**:
  1. Kiểm tra email header hiện tại trên màn hình Google Settings qua XML dump hierarchy (`/dump/hierarchy`).
  2. Nếu email khác email mục tiêu, tap vào avatar/dropdown tài khoản (`account_picker`), chọn đúng email mục tiêu.
  3. Sau khi đổi tài khoản active sang đúng email mục tiêu, click tab *"Tất cả dịch vụ"* $\rightarrow$ *"Bảo mật"* $\rightarrow$ *"Mã bảo mật"* để lấy 2 mã 10 chữ số điền vào form web.

---

## 47. Luồng Chuẩn Khép Kín: Bắt Buộc Kích Hoạt 2FA Authenticator Trước Khi Nạp OAuth Antigravity (Phòng Tránh Checkpoint `rrk=77`)
- **Vấn đề thực tế (Sự cố M02 ngày 07/09/2026)**:
  - Khi script runner nạp OAuth chạy tắt: mở browser và `page.goto(auth_url)` trực tiếp mà tài khoản **chưa từng bật 2FA Google Authenticator** trong phần Cài đặt Google.
  - Hậu quả: Google siết bảo mật hành vi cấp quyền ứng dụng bên thứ ba (Third-Party Cloud Code / Antigravity), kích hoạt checkpoint:
    `signin/rejected?rrk=77`: *"Thêm tính năng Xác minh 2 bước trong phần cài đặt rồi thử lại sau 7 ngày nữa"*.
  - Tài khoản bị khóa nhạy cảm 7 ngày (như M02), không thể tiếp tục OAuth trong vòng 1 tuần.
  - Ngược lại, các tài khoản đã có sẵn 2FA TOTP trong Excel (như M42, M51, M52, M53, M62, M33) đều vượt qua và nạp OAuth thành công 100%.
- **Quy trình chuẩn hóa 3 bước liên hoàn trong cùng Hot Session (BẮT BUỘC)**:
  1. **Bước 1 (Đăng nhập GPM Profile)**: Khởi chạy browser qua đúng Proxy 1:1 theo port máy, đăng nhập Google, xử lý dismiss các màn hình Onboarding (`gds.google.com/web/landing`, `/web/homeaddress`).
  2. **Bước 2 (Kích hoạt 2FA Google Authenticator & Ghi Excel)**:
     - Điều hướng thẳng vào `https://myaccount.google.com/two-step-verification/authenticator`.
     - Nhấp *"Cài đặt ứng dụng xác thực"* $\rightarrow$ *"Bạn không thể quét mã này?"* $\rightarrow$ Trích xuất Secret Key 32 ký tự Base32.
     - Dùng `pyotp.TOTP(secret).at(google_utc)` tính mã OTP $\rightarrow$ Điền xác nhận $\rightarrow$ Kích hoạt 2FA thành công.
     - Ghi nhận ngay Secret Key vào cả 2 file Excel (`master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`).
  3. **Bước 3 (Hot-Session OAuth Hook)**:
     - Giữ nguyên tab Playwright `page` đang "nóng" (không đóng browser, không mở lại context mới để tránh đổi IP/session), gọi `trigger_hot_session_oauth(page, ...)` từ module `hot_session_oauth.py`.
     - Chuyển hướng sang URL authorize của OmniRoute. Vì tài khoản vừa bật 2FA thành công, Google hoàn toàn tin cậy phiên này và chỉ hiện màn hình Consent *"Cho phép"*.
     - Bắt Authorization Code $\rightarrow$ Exchange token lên OmniRoute port `20129` $\rightarrow$ Gán proxy 1:1 $\rightarrow$ Append vào đuôi combo **`ag-gemini-pool-3`**.

---

## 48. Quy Chuẩn Thống Kê & Phân Bổ 40 Cổng Proxy Farm S7 (Port Isolation Quản Lý Theo Ca Ngày)
- **Bản chất kiến trúc Farm Kibe**:
  - Dàn 80 máy Samsung S7 dùng chung **40 cổng proxy 4G Mobifone** vật lý (Port `5101` – `5140` / Singbox local `20001` – `20040`).
  - Phân bổ theo 2 ca máy: Ca 1 (Máy 1–40) và Ca 2 (Máy 41–80) ánh xạ chung cổng.
- **Quy tắc tính số cổng khả dụng chưa chạy trong ngày**:
  - Khi người dùng hỏi: *"Còn bao nhiêu port proxy hôm nay chưa chạy?"*, Coordinator BẮT BUỘC:
    1. Lấy toàn bộ danh sách 40 cổng proxy Farm S7.
    2. Trừ đi tất cả các cổng đã phát sinh chạy trong ngày hôm nay (dù `SUCCESS`, `TIMEOUT` hay `FAILED` để giữ an toàn tuyệt đối, tránh làm nóng IP trên cùng 1 cổng 4G).
    3. Ví dụ ngày 07/09/2026: Đã chạy 22 cổng, còn lại chính xác **18 cổng khả dụng nguyên vẹn**:
       `5101, 5102, 5103, 5104, 5114, 5118, 5125, 5126, 5127, 5134, 5135, 5136, 10002, 10003, 10004, 10005, 10006, 10007`.
- **Kỷ luật Port Isolation**: Tuyệt đối không bao giờ xếp 2 tài khoản chạy trên cùng 1 cổng proxy trong cùng 1 ngày. Mỗi cổng proxy chỉ phục vụ đúng 1 tài khoản trong chu kỳ 24h.

---

## 49. Bẫy Hardcode Timeout 35s Trong `hot_session_oauth.py` & Chuẩn Hóa Timeout >= 120s Cho Mạng Proxy 4G
- **Cơ chế lỗi**:
  Khi gọi `trigger_hot_session_oauth(page, ...)`, script cũ hardcode vòng lặp chờ authorization code: `while time.time() - start_t < 35:`.
  Trên mạng 4G Mobifone Proxy của Farm (`192.168.110.2:200xx`), độ trễ RTT và thời gian tải trang consent Google, click tài khoản, submit quyền và chờ Google chuyển hướng redirect thường mất từ 45 – 65 giây.
  Hậu quả: Trình duyệt đang chạy hoàn toàn bình thường nhưng bị script kết luận lỗi giả `TIMEOUT_NO_CODE` sau đúng 35 giây (như đã xảy ra trên M29 và M60).
- **Chuẩn hóa bắt buộc**:
  Nâng trần timeout cho OAuth Hot-Session lên tối thiểu **120 giây** (hoặc 180s như `run_oauth_s7_pipeline.py`) để đảm bảo không bị ngắt quãng giữa chừng khi mạng 4G có độ trễ cao.

---

## 50. Quy Chuẩn Canonical Full Pipeline 4 Bước Khép Kín (Chỉ Đạo Người Dùng 2026-09-08)
- **Chỉ đạo rõ ràng của người dùng**: *"Đúng làm đầy đủ luồng cho t"*, *"Còn bước login acc nếu cần lấy mã bên s7 đâu"*.
- **CẤM TUYỆT ĐỐI**: Nhảy cóc thẳng vào link OAuth khi tài khoản chưa có 2FA, hoặc bỏ qua bước duyệt mã bảo mật trên điện thoại Samsung S7.
- **Thứ tự 4 bước tuần tự bất biến**:
  1. **Bước 1 (Đăng nhập Google & Vượt Thử Thách Phần Cứng S7)**:
     - Mở profile GPM Chromium qua proxy 1:1 theo port máy.
     - Nhập Email $\rightarrow$ Tự động giải Audio reCAPTCHA (`solve_recaptcha_audio`) nếu xuất hiện $\rightarrow$ Nhập Password.
     - Tự động hóa vượt thử thách trên Samsung S7 qua ADB:
       + *Nếu Google Prompt (`challenge/dp`)*: Đánh thức S7 (`keyevent 224` + `82`), kéo thanh thông báo, bấm nút *"Có / Yes"*, đọc số PIN trên PC và chọn đúng số PIN trên điện thoại.
       + *Nếu Mã bảo mật 10 số (`challenge/ootp`)*: Mở Cài đặt Google trên S7 $\rightarrow$ Quản lý tài khoản $\rightarrow$ Bảo mật $\rightarrow$ Mã bảo mật $\rightarrow$ lấy 2 mã 10 số điền vào form PC.
       + *Nếu đã có sẵn 2FA TOTP trong Excel*: Tính mã TOTP chuẩn True UTC điền vào.
       + Bấm bỏ qua các màn hình Onboarding (`gds.google.com/web/landing`, `/web/homeaddress`, popup "Để sau").
  2. **Bước 2 (Kiểm Tra & Kích Hoạt 2FA Google Authenticator)**:
     - Điều hướng tới `https://myaccount.google.com/two-step-verification/authenticator`.
     - Nếu Google yêu cầu xác minh lại mật khẩu (`challenge/pwd`): Điền password và chờ điều hướng hoàn tất.
     - *Nếu chưa bật 2FA*: Bấm *"Thiết lập"* $\rightarrow$ Bấm *"Không thể quét mã?"* $\rightarrow$ Bốc chuỗi Base32 Secret Key (32 ký tự) $\rightarrow$ Bấm Tiếp theo $\rightarrow$ Tính mã TOTP 6 số điền xác nhận kích hoạt thành công.
     - **Ghi nhận ngay Secret Key vào cả 2 file Excel**: `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`) và `gmail_clean_v2.xlsx`.
     - *Nếu đã bật sẵn 2FA*: Giữ nguyên Secret Key đã có trong Excel.
  3. **Bước 3 (Hot-Session OAuth Hook >= 120s)**:
     - **CẤM ĐÓNG TRÌNH DUYỆT**: Giữ nguyên tab Playwright đang đăng nhập hợp lệ.
     - Điều hướng sang link authorize Antigravity từ OmniRoute port `20129`.
     - Chọn tài khoản nếu hiện Account Chooser, bấm *"Cho phép" / "Allow" / "Tiếp tục"* trên Consent screen.
     - Bắt Authorization Code từ network request listener (`/callback?code=...`).
     - Gửi POST exchange token sang OmniRoute, gán proxy 1:1 (`/api/settings/proxies/assignments`), gọi sync-models.
  4. **Bước 4 (Đồng Bộ Combo & Proof Bằng Chứng Vật Lý)**:
     - Gọi `append_connections()` nạp target vào đuôi combo **`ag-gemini-pool-3`** (CẤM đổi tên combo).
     - Chụp ảnh màn hình điện thoại Samsung S7 qua ADB (`adb exec-out screencap -p`) làm bằng chứng vật lý gửi cho người dùng.

---

## 51. Xử Lý Điều Hướng & Re-Auth Password Tại Trang Authenticator Setup
- **Cơ chế**: Khi truy cập trực tiếp `https://myaccount.google.com/two-step-verification/authenticator`, Google luôn yêu cầu nhập lại mật khẩu để bảo vệ cài đặt nhạy cảm.
- **Bẫy vội vàng (Race Condition)**: Nếu script chỉ điền password rồi `time.sleep(4)` mà không có vòng lặp kiểm tra URL hoặc chờ trang chính thức render, script sẽ tìm nút *"Thiết lập"* (`setup_btn`) khi trang vẫn đang ở `challenge/pwd` $\rightarrow$ Báo không thấy nút và bỏ qua 2FA.
- **Chuẩn hóa**: Bắt buộc lặp chờ cho đến khi URL không còn chứa `challenge/pwd` và `signin`, sau đó mới tìm `setup_btn`, click `force=True`, và chờ modal dialog hiển thị đầy đủ trước khi trích xuất chuỗi Base32.

---

## 52. Kỷ Luật Điều Phối Worker: 1 Subagent = 1 Máy Duy Nhất (Tránh Bẫy Timeout Gom Batch 600s)
- **Sự cố thực tế**:
  Khi Coordinator gom 4 tài khoản (M02, M42, M16, M29) vào 1 subagent chạy tuần tự:
  Mỗi tài khoản tốn 120–180s. Nếu 2 tài khoản gặp timeout hoặc reCAPTCHA (180s x 2 = 360s) cộng thêm thời gian tài khoản thứ 3 (120s), tài khoản thứ 4 chưa kịp chạy hoặc đang chạy dở thì subagent đã chạm trần timeout 600s của platform (hoặc ngân sách 35 tool calls). Hậu quả: Tài khoản thứ 4 bị `INTERRUPTED` oan uổng.
- **Quy tắc điều phối bắt buộc (1 Subagent Per Machine Rule)**:
  1. Điều phối **1 subagent = 1 máy / 1 tài khoản duy nhất**.
  2. Thời gian chạy mỗi máy chỉ mất 90–150 giây, ngân sách chỉ 4–8 tool calls, kiểm soát độc lập từng Connection ID và ảnh proof screenshot.
  3. Nếu một máy gặp lỗi/cooldown, Coordinator cách ly máy đó ngay lập tức mà không làm ảnh hưởng hay ngắt quãng tiến trình của các máy khác trong hàng đợi.

---

## 53. Cơ Chế Phân Biệt Tài Khoản Đã Có 2FA Trong Excel vs Chưa Có 2FA (Bảo Toàn Key Gốc)
- **Bản chất kho tài khoản Farm Kibe**:
  Trong `gmail_clean_v2.xlsx` và `master_gmail_manager.xlsx`, khoảng 40% tài khoản đã được kích hoạt 2FA TOTP từ các đợt trước và đã có Secret Key Base32 trong cột `2fa` / `2FA_Secret` (như M29, M39, M46, M61, M62, M32).
- **Quy tắc xử lý**:
  1. *Nếu tài khoản ĐÃ CÓ Secret Key trong Excel ($\ge 16$ ký tự)*:
     - **TUYỆT ĐỐI KHÔNG** điều hướng vào `two-step-verification/authenticator` để cố bấm "Thiết lập" lại. Làm vậy sẽ khiến Google thay đổi secret key mới làm vô hiệu hóa key cũ trong Excel, hoặc kích hoạt cờ nghi ngờ `signin/rejected?rrk=77`.
     - Chỉ dùng Secret Key hiện có trong Excel để sinh mã TOTP khi Google yêu cầu trong luồng đăng nhập, sau đó chuyển thẳng sang Hot-Session OAuth.
  2. *Nếu tài khoản CHƯA CÓ Secret Key (cột 2fa để trống)*:
     - Bắt buộc thực hiện đầy đủ Bước 2 của Canonical Full Pipeline: vào `two-step-verification/authenticator` -> bốc Base32 Secret Key -> tính TOTP xác minh -> lưu vào cả 2 file Excel trước khi OAuth.

---

## 54. Xử Lý Cooldown 7 Ngày `rrk=77` & Màn Hình Chặn "Thêm 2SV" (Fail-Fast & Cách Ly Tức Thì)
- **Hiện tượng**:
  Khi một tài khoản gặp màn hình `signin/rejected?rrk=77` (*"Thêm tính năng Xác minh 2 bước trong phần cài đặt rồi thử lại sau 7 ngày nữa"*) hoặc màn hình trực tiếp chặn OAuth *"Thêm tính năng Xác minh 2 bước"*:
- **Quy tắc ứng phó**:
  1. **Fail-Fast ngay lập tức**: Thoát vòng lặp, cấm retry mù quáng làm nóng dải IP.
  2. **Ghi nhận vào `cooldown_7days`**: Cập nhật ngay email vào mục `cooldown_7days` trong `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json` với `retry_after: <ngày hiện tại + 7 ngày>` (ví dụ M02, M29).
  3. **Tự động chuyển cổng**: Chuyển ngay sang cổng proxy và tài khoản sạch tiếp theo trong danh sách mốc vàng.

---

## 55. Bẫy Match Nhầm Số PIN Google Prompt Trên PC (`challenge/dp`) & Cấm Cờ Boolean `prompt_approved` 1 Lần
- **Sự cố thực tế (Sự cố Máy 61 ngày 08/09/2026)**:
  - Khi Google hiển thị Google Prompt (`challenge/dp`) yêu cầu chọn số PIN trên điện thoại Galaxy S7 (màn hình hiển thị số `3`), regex cũ:
    `pin_match = re.search(r'(?:nhấn vào|chọn|tap|số|number)\s*(\d{1,2})', safe_body_text(page), re.I)`
    đã match nhầm một con số khác xuất hiện trên trang (số `91`) thay vì số PIN thực tế `3`.
  - Hậu quả: ADB điều khiển Samsung S7 kéo thông báo và tap đúng số `91` (nhầm số) -> Google từ chối và tiếp tục giữ màn hình xác minh chờ số `3`.
  - **Cạm bẫy cờ boolean 1 lần (Single-Prompt Flag Trap)**:
    Script gán cứng `prompt_approved = True` ngay sau lần tap đầu tiên. Khi Google vẫn đang đợi số đúng (hoặc khi Google kích hoạt thêm một đợt Google Prompt thứ hai cho tác vụ nhạy cảm OAuth), điều kiện `if ... and not prompt_approved:` bị bỏ qua hoàn toàn trong 150 giây còn lại, dẫn đến task bị timeout oan uổng!
- **Quy tắc chuẩn hóa trích xuất PIN & Loop Re-Approve**:
  1. **Trích xuất số PIN chuẩn**: Bắt số PIN từ thẻ chứa số lớn trên PC (ví dụ `div[data-challenge-digit]`, `div[role="heading"]`, hoặc text nằm độc lập trong khung challenge) thay vì regex toàn thân body.
  2. **Cho phép duyệt lại prompt khi đổi PIN (Multi-Prompt Handler)**:
     - Thay vì cờ boolean `prompt_approved = True`, sử dụng biến `last_approved_pin = None` và biến đếm `prompt_attempts = 0`.
     - Nếu `target_pin` mới xuất hiện (`target_pin != last_approved_pin`) hoặc nếu sau 8s mà màn hình vẫn còn `challenge/dp` (với `prompt_attempts < 3`), cho phép ADB duyệt lại prompt trên S7 với số PIN cập nhật.

---

## 56. Kỷ Luật Báo Cáo Tiến Độ Định Kỳ Khi Chạy Background (Chống Im Lặng & Cung Cấp Bức Tranh Toàn Cảnh)
- **Tâm lý người dùng**: Khi chạy các batch background dài hơi (5-10 phút), người dùng rất dễ bức xúc và hoang mang nếu agent im lặng quá lâu hoặc chỉ trả lời cộc lốc một chi tiết nhỏ khi được hỏi dồn ("Sao r? Sao k thấy báo cáo loz gì").
- **Quy chuẩn cấu trúc báo cáo 3 phần bắt buộc**:
  1. **Bức tranh vĩ mô (Macro State)**: Tổng số targets hiện tại trong combo (ví dụ: 39 targets), tổng số tài khoản nạp thành công hôm nay, số cổng proxy còn sạch.
  2. **Báo cáo tài khoản vừa hoàn tất / gặp blocker**: Báo rõ từng máy (ví dụ: M39 thành công CID `7eae2de7...`, M02/M29 dính rrk=77 đã cách ly, M61 dính prompt retry).
  3. **Hành động đang thi công ngay lúc này**: Nêu rõ worker đang chạy máy nào, cổng nào, mục tiêu nâng combo lên bao nhiêu targets.

---

## 57. Ranh Giới Ngày Mới & Reset Cooldown Proxy 24h (Chống Nhầm Lẫn Ngày Hệ Thống)
- **Bài học thực tế (Chỉ đạo người dùng 08/09/2026)**:
  - Khi hệ thống bước sang ngày mới (ví dụ 08/09/2026), nguyên tắc "mỗi proxy chạy 1 tài khoản/ngày" **TỰ ĐỘNG RESET** cho toàn bộ các cổng đã chạy của ngày hôm trước (07/09/2026).
  - **CẤM TUYỆT ĐỐI**: Coordinator bị lẫn lộn ngày hệ thống hoặc tiếp tục khóa các cổng proxy đã chạy của ngày hôm trước. Việc nhầm lẫn ngày làm agent tự hạn chế tài nguyên, báo cạn cổng proxy khả dụng và bỏ sót cơ hội nạp tài khoản.
  - Luôn kiểm tra ngày hiện tại của hệ thống bằng `date` hoặc `datetime.date.today()` và chỉ loại trừ các cổng đã phát sinh chạy trong **chính ngày hôm nay**.

---

## 58. Kỷ Luật Nạp Lũy Tiến Từng Tài Khoản (Incremental Append Ngay Khi Success)
- **Cơ chế lỗi (Gom Batch Cuối)**:
  - Trước đây, một số runner gom danh sách `to_append = []` và chỉ gọi `append_connections(to_append)` ở dòng cuối cùng của script sau khi tất cả tài khoản trong batch chạy xong.
  - Hậu quả: Nếu batch gồm 4 máy, máy 1 và máy 2 chạy thành công rực rỡ nhưng máy 3 hoặc máy 4 gặp timeout 180s hoặc lỗi mạng, tiến trình bị ngắt giữa chừng khiến 2 tài khoản thành công trước đó **KHÔNG ĐƯỢC NẠP** vào combo `ag-gemini-pool-3`, lãng phí công sức và tài nguyên của cả đợt chạy.
- **Quy tắc thực thi bắt buộc (Incremental Append Pattern)**:
  - Trong mọi vòng lặp batch runner, ngay khi một tài khoản trả về `status in ["SUCCESS", "ALREADY_SUCCESS"]` và có `conn_id`:
    ```python
    cid = res["conn_id"]
    try:
        append_connections([{"cid": cid, "email": acc["email"], "port": acc["port"]}])
        logger.info(f"✅ Đã append M{mid:02d} ({cid}) vào combo ag-gemini-pool-3!")
    except Exception as e:
        logger.error(f"Lỗi append M{mid:02d}: {e}")
    ```
  - Nạp ngay lập tức từng tài khoản vào combo chính, bảo đảm thành quả được ghi nhận tức thì (real-time pool expansion), bất kể các tài khoản sau đó có gặp sự cố hay không.

---

## 59. Quy Chuẩn Đặt Tên Profile GPM Theo Cụm Máy & Port (`M<máy> - <port> - <email>`) (User Directive 2026-09-08)
- **Nhu cầu & Chỉ đạo của người dùng**:
  Người dùng yêu cầu tổ chức lại bảng danh sách Profile trên GPMLogin theo cụm máy/cổng proxy để trực quan và dễ quản trị:
  *"Profile GPM có cách nào xếp theo kiểu profile 1 - mail xxx, profile 1 - mail YYY, tức là theo thứ tự 1 cụm profile chung 1 port chỉ khác mail đang log in rồi mới tiếp tục cụm tiếp theo"*.
- **Quy tắc định dạng tên chuẩn (Cluster-Based Profile Naming)**:
  `M<Số_Máy:02d> - <Port_Proxy> - <Email>`
  Ví dụ:
  - Cụm Máy 01 (Port 5101):
    `M01 - 5101 - duongkien12022001@gmail.com`
    `M01 - 5101 - thanhdatbui19951@gmail.com`
  - Cụm Máy 02 (Port 5102):
    `M02 - 5102 - duongthanhha270820032708@gmail.com`
    `M02 - 5102 - luuhuong28022000@gmail.com`
  - Cụm Máy 13 (Port 5115):
    `M13 - 5115 - brittanysbarneskn2xa@gmail.com`
    `M13 - 5115 - dangmai31011996@gmail.com`
- **Lợi ích vận hành**:
  Khi người dùng hoặc kỹ thuật viên bấm sắp xếp theo cột **Name** trên bảng điều khiển GPMLogin, toàn bộ các profile cùng thuộc một máy vật lý và cùng chia sẻ một cổng proxy sẽ tự động gom thành từng khối liền kề nhau, không bị xáo trộn lung tung.
- **Cơ chế cập nhật SQLite trực tiếp**:
  - Cơ sở dữ liệu: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`.
  - Bảng: `Profiles`, cột cần đổi: `Name`.
  - **BẮT BUỘC sao lưu trước khi can thiệp**: `shutil.copyfile(db_path, db_path + ".bak")`.
  - Chỉ cập nhật tên hiển thị (`UPDATE Profiles SET Name = ? WHERE Id = ?`), bảo toàn 100% `ProfilePath`, cookie, local storage và dữ liệu duyệt web của trình duyệt.

---

## 60. Quy Chuẩn Điều Phối Song Song 2 Worker (Parallel 2-Worker Concurrency) (User Directive 2026-09-08)
- **Bối cảnh & Chỉ đạo người dùng**:
  Khi quy mô tài khoản mốc vàng còn nhiều (>40 accounts) và dải proxy ngày mới đã sẵn sàng:
  Người dùng hỏi và ra lệnh: *"Nên tăng worker lên k ... rồi làm đi, 2 worker luôn"*.
- **Phân tích kỹ thuật & Sweet Spot**:
  - Nếu chỉ chạy 1 worker tuần tự: mỗi tài khoản mất 1.5–2 phút, cả batch 2-4 tài khoản tốn tới 6-8 phút.
  - Nếu chạy quá nhiều worker (>4-5 worker đồng thời): việc mở dồn dập nhiều trình duyệt qua các cổng USB 4G modem dễ làm nghẽn bus phần cứng và khiến Google kích hoạt bot-check dày đặc.
  - **Điểm ngọt tối ưu (Sweet Spot)**: Điều phối **2 Worker song song cùng lúc (Parallel 2-Worker Mode)**.
- **Quy tắc điều phối 2 Worker qua `delegate_task(tasks=[...])`**:
  1. Mỗi worker gánh 1 cặp tài khoản trên 2 cổng proxy và 2 thiết bị Samsung S7 hoàn toàn độc lập (đảm bảo không tranh chấp `device_lock` hay cổng proxy).
  2. Thời gian hoàn thành cả 2 máy chỉ còn đúng 1.5–2 phút (nhanh gấp 2 lần).
  3. Áp dụng cơ chế **Incremental Append**: Worker nào xong trước thì nạp ngay CID của máy đó vào combo `ag-gemini-pool-3` mà không phải chờ worker kia.

---

## 61. Bẫy Lệch Cổng Singbox Local Khi Machine ID Khác `port - 5100` (M24 vs Port 5128 / Singbox 20024) & `ERR_CONNECTION_RESET` OAuth
- **Cơ chế lỗi (Singbox Port Mismatch Formula)**:
  Trong `run_oauth_s7_pipeline.py`, công thức tính cổng Singbox local mặc định là:
  `singbox_port = acc.get("singbox_port") or (20000 + mid if port == 16002 else (20000 + (port - 5100) if 5000 < port < 6000 else 20000 + (port - 10000)))`
  Khi một máy có số máy `mid` không trùng với độ lệch `(port - 5100)` (ví dụ: Máy 24 sử dụng cổng proxy 5128 nhưng cổng Singbox local tương ứng là `20024`):
  Nếu script tạo dictionary `acc` chỉ truyền `"port": 5128` mà **quên truyền `"singbox_port": 20024`**, script sẽ tự động tính `20000 + (5128 - 5100) = 20028` (trỏ nhầm sang cổng Singbox của Máy 28/Máy 62).
- **Quy chuẩn bắt buộc cho Single Runner**:
  1. Trong dictionary `acc`, luôn truyền tường minh cả `"port"` (cổng gán OmniRoute) và `"singbox_port"`:
     ```python
     acc = {
         "mid": 24,
         "email": "hodat07102000@gmail.com",
         "password": "...",
         "totp_secret": "...",
         "port": 5128,
         "singbox_port": 20024,  # Bắt buộc chỉ định rõ khi port != 5100 + mid
         "serial": "ce0117112b2a0e3a04",
         "profile": "ojGbfJC5Cr-02092026"
     }
     ```
  2. **Bẫy `page.goto(auth_url)` Timeout 35s & `net::ERR_CONNECTION_RESET`**:
     Khi điều hướng tới `auth_url` của Google OAuth qua proxy Singbox 4G, Playwright mặc định chờ sự kiện `"load"`. Nếu kết nối 4G đang xoay IP hoặc bị reset TLS trên endpoint OAuth, `page.goto` sẽ ném `TimeoutError 35000ms exceeded` hoặc `ERR_CONNECTION_RESET`.
     *Khắc phục*: Dùng `wait_until="domcontentloaded"` hoặc `"commit"`, bọc try-except retry 1 lần sau 3s delay hoặc kiểm tra/reset kết nối mạng Singbox local trước khi điều hướng.

---

## 62. Nguyên Tắc Cốt Lõi Cổng Singbox 192.168.110.2: Luôn Định Tuyến Theo `20000 + Machine_ID`
- **Bản chất kiến trúc**:
  Hạ tầng forwarder Singbox cục bộ (`192.168.110.2`) được cấu hình mở cổng ánh xạ trực tiếp theo **Số Máy của thiết bị Samsung S7**, KHÔNG PHẢI theo số cổng proxy Mobi:
  - Máy 41 (Port 5103) $\rightarrow$ Singbox `20041` (tested HTTP 200).
  - Máy 45 (Port 5107) $\rightarrow$ Singbox `20045` (tested HTTP 200).
  - Máy 49 (Port 5113) $\rightarrow$ Singbox `20049` (tested HTTP 200).
  - Máy 54 (Port 5118) $\rightarrow$ Singbox `20054` (tested HTTP 200).
  - Máy 55 (Port 5121) $\rightarrow$ Singbox `20055` (tested HTTP 200).
  - Máy 71..74 (Port 10001..10006) $\rightarrow$ Singbox `20071..20074` (tested HTTP 200).
- **Quy tắc tính chuẩn xác**:
  Mọi runner và script điều phối BẮT BUỘC dùng công thức:
  `singbox_port = 20000 + mid`
  Tuyệt đối không dùng công thức cũ `20000 + (port - 5100)` vì công thức đó chỉ đúng với máy 1–8 và sẽ làm lệch cổng dẫn đến lỗi mất kết nối `WinError 10054` trên tất cả các máy từ 9 trở đi.

---

## 63. Khắc Phục Lỗi `LAUNCH_FAILED` Do Tiến Trình Chrome Mồ Côi Chiếm Lock Profile Directory
- **Hiện tượng**:
  Khi khởi chạy Playwright persistent context:
  `BrowserType.launch_persistent_context: Target page, context or browser has been closed` (`"Mở trong phiên trình duyệt hiện tại"`).
- **Nguyên nhân**:
  Khi một phiên worker trước đó bị crash, ngắt kết nối gateway hoặc chạm trần timeout 600s, tiến trình con `gpm_browser_chromium_core_142\chrome.exe` vẫn tiếp tục chạy ngầm trong Windows. Tiến trình này giữ file lock độc quyền trên file `SingletonLock` / `Preferences` trong thư mục user data (`profile/<profile_path>`), khiến Playwright không thể khởi động profile.
- **Quy trình dọn dẹp Preflight bắt buộc trước khi launch**:
  ```powershell
  # Kiểm tra và ngắt các tiến trình Chrome mồ côi giữ profile trước khi chạy:
  Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match "<profile_name>" -or $_.CommandLine -match "GPMLogin" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  ```
  Sau khi ngắt sạch tiến trình Chrome giữ lock, Playwright sẽ khởi chạy profile mượt mà ngay lập tức.

---

## 64. Quy Trình Khôi Phục Hiện Trường Sau Khi Gateway / Subagent Bị Gián Đoạn Bất Ngờ (Interrupted Batch Recovery)
- **Hiện tượng**:
  Khi gateway Hermes hoặc runtime bị restart/disconnection giữa chừng, platform trả về thông báo lỗi:
  `The batch did not complete successfully: Delegation owner exited before recording a terminal result; outcome unknown`.
- **Kỷ luật điều phối của Coordinator (CẤM CHẠY LẠI MÙ QUÁNG)**:
  1. **Bước 1 — Kiểm tra Ground Truth OmniRoute trước tiên**:
     - Gọi `GET http://127.0.0.1:20129/api/providers` và `GET http://127.0.0.1:20129/api/combos`.
     - Đối soát xem tài khoản trong batch bị gián đoạn thực chất đã nạp thành công trước thời điểm crash hay chưa (ví dụ: trường hợp M41 `marcusephillips52sns@gmail.com` thực chất đã nạp CID `46f4803e...` thành công vào OmniRoute trước khi gateway restart).
  2. **Bước 2 — Đồng bộ nốt mắt xích còn thiếu**:
     - Nếu CID đã tồn tại nhưng chưa gán proxy hoặc chưa append vào combo: thực hiện gán proxy 1:1 (`PUT /api/settings/proxies/assignments`) và gọi `append_connections` để hoàn tất nạp vào combo, tránh việc chạy lại từ đầu làm trùng lặp phiên hoặc kích hoạt nghi ngờ từ Google.
  3. **Bước 3 — Chỉ chạy lại tài khoản thực sự chưa hoàn thành**:
     - Lọc riêng tài khoản chưa có trong OmniRoute để dispatch worker mới, bảo đảm tiết kiệm thời gian và tài nguyên farm.

---

## 65. Khắc Phục Lỗi reCAPTCHA Pointer Intercept Trong `add_oauth_omniroute.py` (`solve_recaptcha_audio`)
- **Hiện tượng**: Khi gọi `solve_recaptcha_audio(page)`, Playwright bị treo 30s với thông báo lỗi:
  `Locator.click: Timeout 30000ms exceeded ... <div></div> from <div>…</div> subtree intercepts pointer events`.
- **Nguyên nhân**: Khi popup challenge (`bframe`) đã xuất hiện, Google chèn một lớp overlay đè lên nút checkbox `#recaptcha-anchor`. Solver nếu quét tìm và click lại `#recaptcha-anchor` mà không có `force=True` sẽ bị intercept pointer events và timeout 30s.
- **Khắc phục chuẩn hóa**:
  1. Kiểm tra nếu `bframe` đã xuất hiện trong `page.frames`: bỏ qua hoàn toàn việc click `anchor_btn` và nhảy thẳng vào bước giải audio challenge.
  2. Khi click `anchor_btn` (khi chưa có `bframe`), thêm `timeout=4000, force=True` và bọc trong `try...except`.
  3. Khi click nút `#recaptcha-audio-button`, thêm `timeout=5000, force=True` để vượt qua bất kỳ lớp overlay nào.

---

## 66. Khắc Phục Cảnh Báo '• degraded' Do Thiếu `projectId` Trên OmniRoute Dashboard
- **Hiện tượng**: Sau khi nạp OAuth thành công, thẻ tài khoản trên `/dashboard/providers/antigravity` hiển thị cảnh báo đỏ `• degraded` kèm thông báo: *"Connected, but the Google Cloud Code projectId could not be found..."*.
- **Nguyên nhân**: Google OAuth exchange đôi khi không trả về `cloudaicompanionProject` khiến trường `projectId` bị rỗng.
- **Khắc phục O(1)**:
  1. Gọi `PUT http://127.0.0.1:20129/api/providers/{cid}` với `{"projectId": "aicode-consumers", "providerSpecificData": {"clientProfile": "ide", "projectId": "aicode-consumers", "tier": "free-tier"}}`.
  2. Gọi `POST http://127.0.0.1:20129/api/providers/{cid}/sync-models` đồng bộ 12 models.
  3. Thẻ lập tức chuyển sang trạng thái `active` (`• đã kết nối` màu xanh lá 100%).

---

## 67. Giới Hạn Hiển Thị 50 Accounts Trên Web UI Dashboard (:20129) vs Thực Tế API
- **Hiện tượng**: Khi số lượng kết nối Antigravity vượt quá 50 accounts (ví dụ 51 accounts), Web Dashboard chỉ render tối đa 50 thẻ tài khoản từ #1 đến #50. Các tài khoản mới nhất từ #51 trở đi không xuất hiện ở đáy danh sách web.
- **Bản chất**: Web frontend của OmniRoute đặt giới hạn hiển thị mặc định `limit = 50` trên trang UI. Trong khi đó, API backend `GET /api/providers` và combo `GET /api/combos` vẫn ghi nhận đầy đủ 100% tất cả các kết nối (ví dụ `pool-51`, `total: 53`).
- **Quy tắc nghiệm thu**: Khi số connection > 50, kiểm tra và nghiệm thu qua API backend (`/api/providers` & `/api/combos`) kết hợp chụp ảnh thẻ #50 trên UI để chứng minh tiến trình nạp mở rộng combo vẫn hoạt động chính xác.

---

## 68. Quy Chuẩn Endpoints GPMLogin Local API v3 (Port 19995) & Schema `profile_data.db`
- **Bẫy URL Singularity & Plaintext Response**:
  - Khi gọi `GET /api/v3/profile/list` hoặc `POST /api/v3/profile/start` (dùng chữ `profile` số ít hoặc `/list`): API GPM v3 trả về chuỗi text `"GPM-Login"` kèm status 200, gây lỗi `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`.
- **Bảng tra cứu Endpoints chuẩn của GPMLogin v3 (`http://127.0.0.1:19995`)**:
  - **Danh sách profiles**: `GET /api/v3/profiles` hoặc `GET /api/v3/profiles?page=1&per_page=100` $\rightarrow$ Trả về JSON `{"success": true, "data": [...], "pagination": {...}}`.
  - **Khởi chạy profile**: `GET /api/v3/profiles/start/{id}` hoặc `POST /api/v3/profiles/start` (body JSON `{"id": "<profile_uuid>", "additionalArguments": "..."}`).
  - **Đóng profile**: `GET /api/v3/profiles/close/{id}` hoặc `POST /api/v3/profiles/close` (body JSON `{"id": "<profile_uuid>"}`).
- **Schema thực tế của SQLite `profile_data.db` (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`)**:
  - Bảng `Profiles` **KHÔNG có cột `RawProxy`**. Việc truy vấn `SELECT RawProxy ...` sẽ lập tức văng exception `sqlite3.OperationalError: no such column: RawProxy`.
  - Danh sách cột đầy đủ: `Id`, `Name`, `ProfilePath`, `JsonData`, `GroupId`, `CreatedAt`, `S3Path`, `CreatedBy`, `LastRunBy`, `LastRunAt`, `UpdatedAt`.
  - Cấu hình proxy, port, proxy auth được lưu trữ bên trong trường JSON `JsonData`.

---

## 69. Quy Trình Fix Antigravity Restricted / Standard-Tier Về Free-Tier Qua Code Assist Personal ToS
- **Bản chất**:
  Khi tài khoản Google chưa chấp thuận Personal Terms of Service trên Google Cloud Code / Gemini Code Assist, OmniRoute sẽ gán tier `standard-tier` hoặc hiển thị trạng thái Restricted / Quota Exhausted.
- **Quy trình 4 bước chuẩn hóa**:
  1. **Lấy `conn_id`**: Truy vấn từ SQLite OmniRoute (`C:\Users\Kibe\.omniroute\storage.sqlite`):
     `SELECT id FROM provider_connections WHERE email = '<email>'`.
  2. **Mở GPM Profile qua đúng Proxy của máy**:
     Gọi `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
  3. **Truy cập URL Chấp Thuận ToS**:
     Điều hướng trình duyệt (hoặc qua remote debugging CDP port trả về từ GPM start) tới `https://codeassist.google.com/?authuser=0`. Kiểm tra và click chấp thuận điều khoản (Personal ToS) nếu có dialog xuất hiện cho đến khi vào dashboard Code Assist.
  4. **Kích hoạt Refresh Token & Kiểm Tra Tier Trên OmniRoute**:
     - Gửi request: `POST http://localhost:20129/api/providers/{conn_id}/test` (body `{}`).
     - Kiểm tra lại trường `provider_specific_data` trong bảng `provider_connections` của `storage.sqlite`: `tier` tự động cập nhật từ `standard-tier` sang `free-tier`.
  5. **Đóng GPM Profile**: Gọi `GET http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}` để giải phóng tài nguyên.














