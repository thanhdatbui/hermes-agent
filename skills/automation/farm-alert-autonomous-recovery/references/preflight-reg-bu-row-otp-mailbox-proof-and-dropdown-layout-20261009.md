# Preflight Reg Bù: Đối Soát Hòm Thư Graph API, Profile 1 Acc & Chẩn Đoán Cáp Remote

> **Date:** 2026-10-09  
> **Trigger:** Farm Alert: `[PREFLIGHT REG BÙ ROW N]` (Thất bại: ADB offline, Lỗi mở account dropdown, Không lấy được OTP).

---

## 1. Bằng Chứng Hòm Thư Microsoft Graph API (Chống Báo Mồm "Không Nhận Được OTP")
- **Yêu cầu cốt lõi**:
  Khi runner báo lỗi `[7c] Không lấy được OTP từ <email>`, **CẤM TUYỆT ĐỐI** chỉ báo lỗi bằng lời nói.
  User invariant: *"OTP/mail ko về bắt buộc gửi ảnh hòm thư chứng minh, cấm nói mồm"*.
- **Quy trình kiểm chứng O(1)**:
  1. Trích xuất `refresh_token` (col 8) và `client_id` (col 9) từ `D:/OneDrive/TaadaaData/<cluster>/gmail_clean_v2.xlsx`.
  2. Tra đổi lấy `access_token` qua endpoint `https://login.microsoftonline.com/common/oauth2/v2.0/token`.
  3. Query `https://graph.microsoft.com/v1.0/me/messages` (và các folder `mailFolders` như `Junk Email`).
  4. Nếu không có email nào từ TikTok (`noreply@tiktok.com`) trong khung giờ chạy:
     - Render ảnh snapshot bằng Pillow hiển thị rõ danh sách thư hiện có, thời điểm nhận, tiêu đề, và kết luận "0 thư TikTok".
     - Kiểm tra ảnh qua WinRT OCR trước khi gửi.
     - Đính kèm thẻ `MEDIA:<path_anh>` độc lập cho User duyệt.
  5. Đối soát kho mail `gmail_clean_v2.xlsx` của máy đó để chọn mail dự phòng có token Graph API LIVE sẵn sàng thay thế.

---

## 2. Bẫy Account Switcher Trên TikTok Profile Layout Mới (Chỉ Có 1 Acc Active)
- **Dấu hiệu nhận biết**:
  - Máy mới tạo 1 nick hoặc mới chỉ log 1 tài khoản (`bongbong...` hoặc `letam...`).
  - Runner gọi `[3] Open account dropdown` nhưng văng lỗi `[03_dropdown] Khong mo duoc account dropdown`.
- **Gốc rễ**:
  1. Header profile phiên bản mới không hiển thị nút chevron dropdown (▼) bên cạnh username khi chỉ có 1 tài khoản đăng nhập.
  2. Nút sticky top bar `pmi` ở tọa độ `(540, 150)` không kích hoạt bottom sheet khi chỉ có 1 tài khoản.
  3. Khi fallback vào *Menu hồ sơ (3 gạch)* -> *Cài đặt và quyền riêng tư*: giao diện TikTok khi chỉ có 1 tài khoản **không hiển thị mục "Chuyển đổi tài khoản"**, mà chỉ có mục *"Thêm tài khoản"* (Add account) hoặc *"Đăng xuất"* ở cuối danh sách.
  4. Nếu thao tác swipe chưa cuộn đủ sâu hoặc bị kẹt lại ở màn hình profile, runner sẽ fail-safe thoát ra và báo lỗi.
- **Biện pháp xử lý & Quy trình Đăng xuất An toàn (Safe Sign-Out Flow)**:
  - Kiểm tra số lượng nick thực tế trên máy qua `taikhoan_dat_v2_updated .xlsx` và XML dump.
  - Luôn kiểm tra song song cả hai text selector: `"Chuyển đổi tài khoản"` VÀ `"Thêm tài khoản"` sau mỗi nhịp cuộn trong Cài đặt.
  - **Quy trình Đăng xuất Phá Deadlock trên Máy 1 Acc**:
    1. Khi máy chỉ có 1 nick active, TikTok ẩn toàn bộ Switcher/Add account ở cả Header lẫn Settings.
    2. Thực hiện Đăng xuất: *Menu hồ sơ (3 gạch)* -> *Cài đặt và quyền riêng tư* -> Cuộn đáy -> Bấm *"Đăng xuất"* -> Xác nhận *"Đăng xuất"*.
    3. Mở lại TikTok và vào tab Hồ sơ: TikTok hiển thị màn hình **One-tap Login ("Chào mừng bạn trở lại")**.
    4. **Bảo toàn phiên 100%**: Tất cả các nick cũ được lưu trong danh sách One-tap login, không hề bị mất phiên.
    5. **Mở khóa nút Reg/Login**: Màn hình này cung cấp sẵn nút *"Thêm tài khoản khác"* và *"Bạn không có tài khoản? Đăng ký"* để tiến hành reg tài khoản mới (Row N) bình thường. Sau khi reg thành công nick thứ 2, TikTok sẽ tự động kích hoạt lại menu Switcher chuẩn.

---

## 3. Chẩn Đoán Lỗi Cáp Vật Lý Trên Cụm Admin Remote (`admin-farm`)
- Khi ADB báo `device not found` hoặc `offline` trên thiết bị thuộc cụm Admin (`192.168.110.119:5037`):
  Thực thi lệnh kiểm tra PnP từ xa qua SSH:
  ```bash
  ssh admin-farm "powershell.exe -Command \"Get-PnpDevice | Where-Object { \$_.InstanceId -like '*<serial>*' } | Select-Object FriendlyName, Status, Present, Problem | Format-List\""
  ```
- Nếu `Present: False` hoặc `Problem: CM_PROB_PHANTOM`:
  - Khẳng định 100% cáp USB bị tuột/lỏng hoặc máy mất nguồn tại rack vật lý.
  - Lập tức chuyển trạng thái **L3 BLOCKED** kèm trích xuất PnP Device, không retry trong bóng tối.

---

## 4. TikTok Silent Drop: Cách Ly 2 Tầng Mail Kẹt & Đổi Mail Dự Phòng O(1)
- **Bản chất Silent Drop**:
  - Giao diện TikTok client vẫn đếm ngược 60s, nhưng backend TikTok drop lệnh gửi email sang Microsoft đối với các mail mới/bị nghi ngờ độ trust thấp.
  - Graph API chứng minh hòm thư LIVE 100% nhưng 0 email TikTok về.
- **Cạm bẫy hoàn trả mail (Restore Pitfall)**:
  - CẤM hoàn trả mail kẹt về trạng thái rỗng (`None`) trong `gmail_clean_v2.xlsx`. Việc hoàn trả sẽ khiến `_detect_clean.py` bốc lại đúng mail đó ở các ca reg bù sau (gây lỗi tuần hoàn lặp đi lặp lại).
- **Quy trình cách ly 2 tầng chuẩn hóa**:
  1. *Tầng Excel (`gmail_clean_v2.xlsx`)*: Backup `.bak_<timestamp>` -> Ghi cột 11 (`trạng thái`) = `skip_otp_timeout`.
  2. *Tầng JSON (`registered_emails_blacklist.json`)*: Thêm địa chỉ mail vào danh sách blacklist để loại trừ khỏi detector.
- **Kích hoạt mail dự phòng**:
  1. Đối soát kho mail của máy trong `gmail_clean_v2.xlsx` để lấy mail sạch kế tiếp có Graph API token LIVE.
  2. Dry-run kiểm chứng: `python D:/Taadaa/tools/ensure_row_accounts.py <row> --machines <stt> --dry-run` -> `Có sẵn mail: 1 máy | Cần mua mail: 0 máy`.
  3. Kích hoạt chạy nền có notify: `TAADAA_HOST_CONFIG=".../admin.yaml" python -u D:/Taadaa/tools/ensure_row_accounts.py <row> --machines <stt>` (background=True, notify_on_complete=True).

---

## 5. Hiện Tượng Switcher Đơ / Không Bung Do Văng Phiên Cũ & Kỷ Luật Re-Login Trước (User Rule)
- **Dấu hiệu**:
  - Máy đã có sẵn tài khoản trong tracking (ví dụ Máy 266 có 2 nick: `letam2502`, `bongbong02892`).
  - Khi mở profile TikTok, bấm vào display-name, username, hoặc icon header nhưng Account Switcher hoàn toàn không bung ra (`[03_dropdown] Khong mo duoc account dropdown`).
  - Nếu vào Settings -> Đăng xuất, app rơi vào màn hình One-tap Login ("Chào mừng bạn trở lại") liệt kê các nick cũ (`l***2@hotmail.com`, `o***d@hotmail.com`).
  - Nếu cố ép chạy reg tài khoản mới ngay lúc này, runner văng lỗi `[06_email_option] Không tìm thấy: Email / icon email` vì flow giao diện bị lệch sang nhánh Login của One-tap list.
- **Bản chất nguyên nhân (User insight)**:
  - *"Khả năng do bị văng nên account switcher bấm vào k bung ra"* — Toàn bộ các nick hiện hữu trên máy đã bị hết hạn token / văng phiên (session expired/logged out). TikTok chỉ render view cache tĩnh, không có context phiên active để tải và bung Account Switcher.
- **Quy trình phục hồi chuẩn (Login Phục Hồi Trước — User Directive: "Login luôn mấy acc cũ lại")**:
  1. **Tạm dừng luồng Reg**: Tuyệt đối không cố ép chạy reg tài khoản mới khi các nick cũ trên máy đang ở trạng thái văng phiên.
  2. **Kiểm tra liveness của mail cũ**: Dùng Microsoft Graph API test `refresh_token` + `client_id` của các nick cũ trong `gmail_clean_v2.xlsx`.
  3. **Chạy login phục hồi canonical**:
     ```bash
     ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" \
     TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" \
     python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <stt> --email <old_username_or_email> --ss
     ```
  4. **Phục Hồi Siêu Tốc Qua One-Tap Login (O(1) Quick Tap)**:
     - Khi nick cũ bị văng ra màn hình "Chào mừng bạn trở lại", các phiên này vẫn được app TikTok cache token cục bộ.
     - Thay vì chạy lại flow OTP đầy đủ, chỉ cần tap trực tiếp vào tên account trong danh sách One-tap login (ví dụ tap vào `bongbong02892` hoặc `letam2502`), TikTok sẽ lập tức kích hoạt lại phiên đăng nhập trong vòng 2-3 giây mà không cần OTP!
  5. **Kích hoạt lại Switcher**: Khi có ít nhất 1 nick đăng nhập active thành công, context phiên của app TikTok được khôi phục hoàn toàn -> Account Switcher hoạt động bình thường trở lại, sẵn sàng cho các lượt reg hoặc switch kế tiếp.

---

## 6. Giải Mã Nghi Vấn: "Tại Sao Đăng Nhập Cả 2 Acc Mà Switcher Vẫn Không Bung, Vẫn Ra Màn Chào Mừng Bạn Trở Lại?" (TikTok v46.6.3 / Android 8)
- **Thắc mắc cốt lõi từ User**:
  *"Là sao đáng lẽ đăng nhập cả 2 acc thì account switcher phải bung ra. Chứ sao lại xuất hiện màn chào mừng bạn trở lại nữa"*
- **Bản chất cơ chế thực nghiệm trên thiết bị Samsung Galaxy S7 (Android 8, TikTok v46.6.3)**:
  1. **Tách biệt phiên đơn (Single-Active Session Architecture)**:
     - Trên bản build TikTok v46.6.3 chạy trên Android 8, khi các tài khoản được đăng nhập hoặc khôi phục qua One-tap login, TikTok **chỉ duy trì duy nhất 1 phiên active tại một thời điểm** trong app memory.
     - Khi đang ở trong Profile của bất kỳ nick nào (`bongbong02892` hay `letam2502`), TikTok **cố tình không render menu Account Switcher** (tên hiển thị `sv6` chỉ là plain text, không có mũi tên ▼).
     - Trong mục *Cài đặt và quyền riêng tư*, ở đáy danh sách **chỉ có duy nhất nút "Đăng xuất"** (hoàn toàn không có mục "Chuyển đổi tài khoản" hay "Thêm tài khoản").
  2. **One-Tap Login là Hub Chuyển Đổi Trung Tâm (OS/App One-Tap Hub)**:
     - Với các máy chưa đủ 3+ tài khoản liên kết sâu trong internal account store, màn hình **"Chào mừng bạn trở lại" (One-tap Login)** chính là **Trung tâm chuyển đổi tài khoản** mà TikTok thiết kế cho thiết bị này.
     - Khi bấm "Đăng xuất" từ một nick, TikTok không hề xóa phiên (session token được lưu an toàn vào AccountManager/KeyStore của Samsung). Cả 2 nick đều hiện diện trên danh sách One-tap kèm avatar và email che (`o***d@hotmail.com`, `l***2@hotmail.com`).
     - **Chuyển nick O(1)**: Bấm vào nick nào trong danh sách One-tap là app lập tức vào thẳng Profile nick đó (không hỏi mật khẩu, không hỏi OTP).
     - **Mở rộng slot**: Nút *"Thêm tài khoản khác"* và *"Bạn không có tài khoản? Đăng ký"* luôn nằm cố định ở đáy màn hình One-tap này để tiếp tục thêm các tài khoản tiếp theo.

---

## 7. Pitfalls Kỹ Thuật Khi Chạy tiktok_login_v1.py Trên Cụm Admin (201–280)
1. **Lỗi `RuntimeError: Khong co STT <N> trong ACCOUNTS`**:
   - *Nguyên nhân*: File `social_reg_v1.py` lưu biến cứng `ACCOUNTS` chỉ chứa các máy STT 1–39/80 của Cụm Kibe. Hàm `resolve_device(stt)` trong `tiktok_login_v1.py` tra cứu `ACCOUNTS` nên văng lỗi ngay lập tức khi chạy cho máy Admin (201–280).
   - *Bản vá chuẩn hóa*:
     ```python
     def resolve_device(stt):
         acc = next((item for item in ACCOUNTS if item["stt"] == stt), None)
         if acc and acc.get("device"):
             return acc["device"]
         from project_paths import TARGET_INVENTORY_WORKBOOK
         from scripts.target_inventory import load_machine_devices
         dev = load_machine_devices(TARGET_INVENTORY_WORKBOOK).get(stt)
         if dev:
             return dev
         raise RuntimeError(f"Khong co STT {stt} trong ACCOUNTS")
     ```
2. **Lỗi `VPN GATE BLOCKED: device offline or ADB/USB disconnected (localhost:5037)`**:
   - *Nguyên nhân*: Chạy `tiktok_login_v1.py` độc lập mà quên export `ADB_SERVER_SOCKET`, Xiaowei ADB sẽ mặc định kết nối `localhost:5037` thay vì daemon remote của máy chủ Admin.
   - *Lệnh canonical bắt buộc*:
     ```bash
     ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" \
     TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" \
     python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <target> --ss
     ```
