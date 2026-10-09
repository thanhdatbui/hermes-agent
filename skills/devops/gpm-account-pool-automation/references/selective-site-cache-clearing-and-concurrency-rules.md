# Xóa Cache/Dữ Liệu Theo Site Riêng Biệt & Kỷ Luật Điều Phối Worker Concurrency Trong GPM

## 1. Xóa Dữ Liệu Riêng Biệt Cho 1 Website (Selective Per-Domain Data Clearing)

### Bối cảnh & Yêu cầu nghiệp vụ
Khi một dịch vụ (ví dụ OpenAI / ChatGPT, TikTok, Facebook, Discord) bị khóa tài khoản hoặc cần đăng ký lại tài khoản mới (reg acc free), người dùng muốn **xóa sạch hoàn toàn session của website đó trên profile GPM**, nhưng **BẮT BUỘC giữ nguyên 100% phiên đăng nhập Google / Gmail / YouTube**.

### Fingerprint và cơ chế chống bot (Tại sao không cần đổi Fingerprint)
- **OpenAI / Cloudflare Turnstile** không thực hiện hardware ban như game anti-cheat (EasyAntiCheat / Vanguard).
- Hệ thống nhận diện bot dựa trên:
  1. **Storage & Session Identifiers**: Cookies (`oai-did`, `oaicom-stable-id`, `__Secure-next-auth.session-token`), LocalStorage, IndexedDB (`https_chatgpt.com_*.indexeddb.leveldb`).
  2. **Chất lượng IP mạng**: Dải Proxy di động 4G / Residential (ví dụ Farm Mobi `test.taadaa.click:5101..5138`) có điểm tín nhiệm rất cao.
  3. **Độ chân thực của Browser Fingerprint**: Canvas, WebGL, Audio, User-Agent của profile GPMLogin đang tạo ra hành vi của trình duyệt người dùng thật.
- **Kết luận**: Giữ nguyên Fingerprint và chỉ xóa sạch toàn bộ storage liên quan đến domain mục tiêu là giải pháp tối ưu nhất. Website sẽ coi đây là một trình duyệt sạch vừa mới truy cập lần đầu.

### Kỹ thuật dọn dẹp SQLite Offline an toàn
Thao tác trực tiếp trên dữ liệu profile khi trình duyệt đã đóng (tránh lỗi `WinError 32: The process cannot access the file because it is being used by another process`):

1. **Kiểm tra và đóng trình duyệt**:
   - Gọi API `/api/v3/profiles/stop/{profile_id}`.
   - Đảm bảo không còn tiến trình `chrome.exe` nào đang chạy trên thư mục profile.

2. **Sao lưu trước khi can thiệp (Safe Backup)**:
   - Copy `Default/Network/Cookies` thành `Default/Network/Cookies.bak_<site>`
   - Copy `Default/Login Data` thành `Default/Login Data.bak_<site>`

3. **Xóa Cookies mục tiêu (SQLite)**:
   ```sql
   -- Chỉ xóa domain mục tiêu, bảo toàn 100% Google / YouTube
   DELETE FROM cookies WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%';
   VACUUM;
   ```
   *Đối soát:* Đếm lại số cookie Google (`host_key LIKE '%google%'`) trước và sau khi xóa để xác nhận số lượng không đổi.

4. **Xóa Mật khẩu đã lưu trong trình duyệt (Login Data)**:
   - Tránh việc Chrome tự động gợi ý hoặc autofill tài khoản cũ đã vô hiệu hóa:
   ```sql
   DELETE FROM logins WHERE origin_url LIKE '%openai%' OR origin_url LIKE '%chatgpt%';
   VACUUM;
   ```

5. **Xóa IndexedDB & Cache Storage**:
   - Xóa các thư mục khớp domain trong:
     - `Default/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb`
     - `Default/IndexedDB/https_chatgpt.com_0.indexeddb.blob`
     - `Default/Service Worker/CacheStorage/*chatgpt*`

---

## 2. Kỷ Luật Điều Phối Concurrency: Tại Sao Phải Chạy Tuần Tự vs Song Song

### Bối cảnh
Người dùng thắc mắc: *"Sao k làm nhiều worker mà tuần tự chi v"*.
Điều phối subagent hoặc luồng tự động hóa cần hiểu rõ nguyên tắc: **Song song chỉ an toàn khi các tài nguyên chia sẻ (shared resources) độc lập hoàn toàn**.

### 3 Rào cản bắt buộc phải chạy tuần tự (hoặc nhóm tuần tự):

1. **Trùng kênh nhận OTP Email Khôi Phục (Shared Recovery Email)**:
   - Khi nhiều tài khoản Gmail dùng chung một email khôi phục (ví dụ `thanhdatbui1995@gmail.com`):
   - Nếu chạy song song 2-4 worker cùng lúc, Google sẽ gửi các email OTP về hòm thư trong cùng một cửa sổ thời gian (lookback window).
   - Cơ chế polling IMAP đọc email mới nhất sẽ bị **Race Condition**: Worker A đọc và lấy nhầm mã OTP của Worker B, dẫn đến điền sai mã, làm hỏng phiên đăng nhập và kích hoạt checkpoint bảo mật của Google.
   - **Quy tắc**: Các tài khoản dùng chung một email khôi phục **bắt buộc phải chạy tuần tự**, hoặc phải phân nhóm worker theo email khôi phục khác nhau.

2. **Khóa Thiết Bị Phần Cứng (Device Lock Contention)**:
   - Khi luồng xác minh cần tương tác với điện thoại Samsung Galaxy S7 (đọc Security Code hoặc bấm phê duyệt Google Prompt):
   - Thiết bị USB chỉ có thể nhận lệnh ADB / ATX tuần tự. Nếu 2 worker cùng thao tác trên 1 serial S7:
     - Worker này mở Google Settings đè lên popup xác nhận của Worker kia.
     - Dẫn đến cả 2 worker đều timeout hoặc đọc sai mã.
   - **Quy tắc**: Mỗi serial thiết bị Android chỉ cho phép duy nhất 1 worker chiếm quyền (`acquire_device_lock`).

3. **Cổng Remote Debugging (CDP Port Conflict)**:
   - Khi mở profile GPM, mỗi profile được gán 1 cổng CDP ngẫu nhiên.
   - Việc mở hàng loạt quá nhanh (< 10s stagger) dễ làm crash service GPMLogin Local API hoặc gây nghẽn proxy di động (Proxy 4G farm).
   - **Quy tắc**: Luôn stagger tối thiểu 10s khi mở profile mới và giải phóng port (`kill_chrome_by_port`) ngay sau khi hoàn thành.

4. **Giới Hạn Concurrency GPM & Rò Rỉ Tiến Trình Chrome (Zombie Chrome Leak)**:
   - **Giới hạn Concurrency tuyệt đối**: Worker tự động hóa GPM ChatGPT / OAuth BẮT BUỘC chỉ chạy **tối đa 2 worker song song** (`max_workers <= 2`), timeout 600s. CẤM TUYỆT ĐỐI mở 5-10 worker đồng thời vì sẽ làm nghẽn proxy, quá tải GPMLogin core và kích hoạt hàng loạt lỗi treo.
   - **Rủi ro Zombie `chrome.exe` mồ côi**: Lệnh API `/api/v3/profiles/stop/{profile_id}` KHÔNG đảm bảo 100% tắt sạch `chrome.exe` khi:
     - Trình duyệt kẹt modal *"Bạn có muốn khôi phục trang không? (Restore pages)"*.
     - Kẹt luồng Google Account Chooser hoặc Playwright ngắt đột ngột (Circuit Breaker kích hoạt).
     - Thread pool shutdown nhưng tiến trình con Chromium vẫn tiếp tục chạy ngầm.
   - **Biện pháp khắc phục bắt buộc**:
     - Script worker trong khối `finally` ngoài việc gọi `/api/v3/profiles/stop/{id}` phải kiểm tra và cưỡng chế kill `chrome.exe` liên kết với `--user-data-dir` của profile đó.
     - Sau khi kết thúc batch hoặc chạm Circuit Breaker, BẮT BUỘC kiểm tra và dọn dẹp các `chrome.exe` mồ côi thuộc thư mục `GPMLogin\profile`:
       ```bash
       wmic process where "name='chrome.exe' and CommandLine like '%GPMLogin\\\\profile%'" call terminate
       ```
   - **Phân biệt hiện tượng Desktop**: Khi thấy hàng loạt icon vuông đen có số trên Taskbar (ví dụ `130` -> `160`), đây là các instance điều khiển thiết bị của tool Phone Farm (**`xiaowei.exe`** - XiaoWei Group Control), KHÔNG PHẢI do GPMLogin spam profile. GPM Profile luôn chạy dưới tên `chrome.exe` với icon trình duyệt Chromium.
