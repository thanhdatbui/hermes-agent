# Google Recovery: Offline Security Code (Mã bảo mật 10 số) trên Android S7 vs Push Prompt Pitfall

## Bối cảnh & Hiện tượng (2026-09-06, Máy 36)
Khi đăng nhập Google Account trên trình duyệt GPM (dùng proxy farm) bị sai mật khẩu (hoặc mật khẩu dự phòng không khớp) và kích hoạt luồng "Bạn quên mật khẩu?":
- Thông thường trên nhiều tài khoản, Google gửi Google Prompt (thông báo push "Bạn đang cố đăng nhập?" hoặc yêu cầu chọn số PIN 2 chữ số khớp với trình duyệt).
- **Tuy nhiên**, khi tài khoản Google vẫn đang được add trong Android Settings (`dumpsys account` thấy `Account {name=..., type=com.google}`), Google Recovery thường KHÔNG gửi push notification mà chuyển sang yêu cầu:
  > **"Nhận Galaxy S7 của bạn"**
  > 1. Mở ứng dụng Cài đặt
  > 2. Nhấn vào Google
  > 3. Chọn tài khoản của bạn
  > 4. Nhấn vào Quản lý Tài khoản Google của bạn
  > 5. Chọn tab Bảo mật (cuộn sang phải)
  > 6. Trong phần "Đăng nhập vào Google", nhấn vào **Mã bảo mật** (Security Code)
  > 7. Chọn tài khoản nhận mã -> Nhập mã 10 chữ số vào trình duyệt.

## Bẫy sai lầm & Phân tích nguyên nhân (Root Cause)
1. **Bẫy chờ Push Notification mù quáng**:
   - Automation script chờ đợi thông báo push hoặc quét tìm nút "Có" / "Yes" / "Có, chính là tôi" trên S7.
   - Khi không có push prompt, script kéo statusbar (`cmd statusbar expand-notifications`) và bắt gặp các thông báo hệ thống như:
     - *"Thông báo của Dịch vụ Google Play: Đã cập nhật Tài khoản Google"*
     - *"Thông báo của Dịch vụ Google Play: Bạn sắp hoàn thành việc này .."* (của tài khoản cũ khác trên máy)
   - Tapping vào các thông báo này không dẫn tới màn hình phê duyệt đăng nhập, gây lặp vô hạn và timeout.

2. **Bẫy click "Thử cách khác" (Try another way)**:
   - Khi thấy màn hình yêu cầu Mã bảo mật, nếu script tiếp tục click "Thử cách khác":
     Google lập tức trả về:
     > **"Không thể đăng nhập cho bạn: Bạn không cung cấp đủ thông tin để Google chắc chắn rằng tài khoản này thực sự là của bạn."**
     (Tài khoản bị khóa recovery tạm thời trên IP/browser hiện tại).
   - **Quy tắc bắt buộc**: Khi gặp màn hình yêu cầu Mã bảo mật (Security Code), **CẤM** click "Thử cách khác". Bắt buộc phải lấy mã 10 số từ thiết bị.

## Cách lấy Mã bảo mật (Security Code 10 chữ số) trên S7
- **Mã bảo mật offline**: Đây là mã OTP 10 chữ số được sinh offline theo thuật toán của Google Play Services trên thiết bị đã đăng nhập, có hiệu lực trong 15 phút, không phụ thuộc vào mạng internet hay push notification.
- **Điều hướng trên Android 7/8 (Samsung S7)**:
  1. Mở Cài đặt: `am start -a android.settings.SETTINGS`
  2. Dùng ATX session XML tìm và tap text `"Google"` (hoặc mở Activity Google Settings nếu có).
  3. Tìm `"Quản lý Tài khoản Google của bạn"`.
  4. Nếu máy có nhiều tài khoản, tap chọn đúng email mục tiêu (`dumpsys account`).
  5. Chuyển sang tab `"Bảo mật"` -> tap `"Mã bảo mật"`.
  6. Màn hình hiển thị 2 mã bảo mật gồm 10 chữ số (dạng `XXX XXX XXXX`). Đọc XML qua ATX session để lấy chuỗi 10 số.
  7. Nhập mã 10 số này vào ô `input[type="tel"]` hoặc `input[name="Pin"]` trên trình duyệt GPM và nhấn `Tiếp theo`.
  8. Trình duyệt sẽ mở khóa chuyển sang màn hình **"Tạo mật khẩu mới"** để chuẩn hóa mật khẩu thành công.

## Lưu ý về Proxy Credentials có ký tự đặc biệt (`@`)
- Khi test proxy hoặc cấu hình chuỗi proxy qua curl/requests:
  Ví dụ proxy `mirotik1.taadaa.click:10004:admin@1:admin@1`:
  Ký tự `@` trong username/password làm curl hiểu nhầm host boundary. Bắt buộc URL-encode thành `admin%401:admin%401` khi dùng định dạng URL `http://user:pass@host:port`.

---

## 4. Kỷ Luật Rà Soát Lịch Sử Mật Khẩu & Đổi Mật Khẩu Trên S7 (User Rule 2026-09-06)
- **Chỉ đạo nghiệp vụ**: *"Pass bị sai đó kiểm tra lịch sử lưu gmail đó có chỗ nào lưu pass khác k! K có thì đổi pass ms trên s7 luôn"*.
- **Quy trình 2 bước chuẩn hóa**:
  1. **Rà soát đối chiếu đa nguồn Excel**:
     - Kiểm tra đồng thời cả 3 nguồn: `master_gmail_manager.xlsx` (cả 2 sheet `Master_All` và `Kibe_Farm_S7`), `gmail_clean_v2.xlsx`, và `taikhoan_dat_v2_updated .xlsx`.
     - *Lưu ý*: Trong `taikhoan_dat_v2_updated .xlsx`, cột `PASS` có thể chứa mật khẩu gốc lúc tạo tài khoản (ví dụ `ab1kTXrBThE5i@yu`), còn cột `PASS MAIL` chứa mật khẩu đã đổi sau này (ví dụ `Caoanh11092003@Ks`). Thử cả 2 mật khẩu này trước khi can thiệp khôi phục.
  2. **Đổi mật khẩu mới qua S7 (khi không còn pass nào khớp)**:
     - Trên trình duyệt GPM: bấm *"Bạn quên mật khẩu?"* (Forgot password).
     - Google yêu cầu Mã bảo mật 10 chữ số từ thiết bị S7 (`challenge/ootp`).
     - Lấy mã 10 số qua hàm `get_s7_security_code(machine_id, serial, email)` từ Google Settings trên S7.
     - Điền mã 10 số vào form GPM -> Mở khóa màn hình *"Tạo mật khẩu mới"*.
     - Đặt lại mật khẩu mới chuẩn hóa theo quy tắc Farm (`<Tên><ddMMyyyy>@Ks`), bấm Lưu mật khẩu.
     - Đăng nhập thành công vào `myaccount.google.com` và đồng bộ ngay vào cả 2 file Excel (`master_gmail_manager.xlsx` & `gmail_clean_v2.xlsx`).

---

## 5. Pitfall Môi Trường Python & Playwright trên Host Windows (Shadowing PYTHONPATH)
- **Hiện tượng**: Chạy script Playwright / GPM bị crash ngay tại `from playwright.sync_api import sync_playwright`:
  ```text
  ModuleNotFoundError: No module named 'greenlet._greenlet'
  ```
- **Nguyên nhân**: Môi trường shell (Git Bash / MSYS) tự động export biến môi trường `PYTHONPATH` trỏ vào venv của Hermes agent (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`). Venv này bị lỗi binary C-extension của `greenlet`, khiến mọi lời gọi `python` / `python3` từ bash đều bị ép nạp module lỗi này thay vì môi trường sạch của repo.
- **Cách khắc phục chuẩn**:
  1. Luôn dùng `env -u PYTHONPATH` khi chạy python VÀ CẢ KHI chạy `pip install` từ bash terminal:
     ```bash
     # Cài đặt dependency vào đúng site-packages của python target (tránh bị pip trỏ nhầm vào Hermes venv):
     env -u PYTHONPATH "C:/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe" -m pip install playwright pyotp pydub SpeechRecognition openpyxl requests

     # Chạy script:
     env -u PYTHONPATH "D:/Taadaa/python-envs/automation/Scripts/python.exe" <script.py>
     # Hoặc với Python hệ thống:
     env -u PYTHONPATH "C:/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe" <script.py>
     ```
  2. Hoặc thực thi qua PowerShell (`powershell -NoProfile -Command "& '...'"`).
  3. **Bẫy Pip Satisfied Ảo**: Nếu chạy `python.exe -m pip install` mà KHÔNG có `env -u PYTHONPATH`, pip sẽ báo `Requirement already satisfied` tại `AppData\Local\hermes\...\venv`, nhưng khi chạy script với `env -u PYTHONPATH` sẽ văng `ModuleNotFoundError`. Bắt buộc gỡ biến `PYTHONPATH` cả lúc pip install.
  4. **Lưu ý file helper**: Khi import hàm helper (như `get_s7_security_code` từ `s7_helper_clean.py`), đảm bảo file đó đã đầy đủ các import header (`Optional`, `Tuple`, `re`, `subprocess`, `requests`, `ET`, `logger`), tránh lỗi `NameError: name 'Optional' is not defined`.

## 6. Canonical Scripts Sẵn Có Cho Máy 36 & Máy 38
- Trích xuất S7 Security Code độc lập: `D:\Taadaa\GPM auto\scripts\s7_helper_clean.py` (hàm `get_s7_security_code(machine_id, serial, target_email)`).
- Script hoàn tất nhanh (Fast Finish) Máy 38: `D:\Taadaa\GPM auto\scripts\fast_finish_m38.py` (Playwright CDP, password `Ibhqkdygvmef`, bắt `challenge/dp` tap 540 1362 duyệt S7 `ce06160685310f1c04`, sync Excel).
- Script hoàn tất nhanh (Fast Finish) Máy 36: `D:\Taadaa\GPM auto\scripts\fast_finish_m36.py` (Lấy mã 10 số từ S7 `ce10160ac8f1962305`, forgot password, đặt lại pass `Caoanh11092003@Ks`, sync Excel).
- Script test & hoàn tất luồng login Máy 36: `D:\Taadaa\GPM auto\scripts\test_login_m36.py`.
- Script test & hoàn tất luồng login Máy 38: `D:\Taadaa\GPM auto\scripts\test_login_m38.py`.
- Script tổng hợp chạy cặp M36 & M38: `D:\Taadaa\GPM auto\scripts\finalize_m36_m38_login.py`.

## 7. DOM Selector Pitfalls trên Google Signin v3 (2026)
1. **Bẫy `input[type="email"]` trên trang Identifier**:
   - Trên `https://accounts.google.com/v3/signin/identifier`, input nhập email có `type="text"`, `name="identifier"`, `id="identifierId"`.
   - Selector `input[type="email"]` bị **Timeout 30000ms** vì không tồn tại thuộc tính `type="email"`.
   - **Selector chuẩn**: `input#identifierId, input[name="identifier"], input[type="email"]`.
2. **Bẫy `#forgotPassword` trên trang Password**:
   - Phần tử `#forgotPassword` là một thẻ `<div id="forgotPassword">`, nút bấm thực tế là `<button>` nằm bên trong.
   - Gọi click trực tiếp vào `#forgotPassword` có thể không kích hoạt event click do CSS pointer-events.
   - **Selector chuẩn**: `#forgotPassword button, button:has-text("quên mật khẩu"), button:has-text("Forgot password")`.
   - Cần đặt việc kiểm tra click nút "Quên mật khẩu" bên trong vòng lặp thử thách: nếu URL vẫn còn là `challenge/pwd` thì tiếp tục thử click lại với `force=True` hoặc `.press("Enter")`.
3. **Mật khẩu Máy 38 (`benghowelltpkf1@gmail.com`)**:
   - Mật khẩu `N0spam@@` bị Google từ chối báo sai mật khẩu. Mật khẩu lưu trước đó `Ibhqkdygvmef` được chấp nhận để vượt qua bước mật khẩu và chuyển tiếp sang `challenge/dp`.
4. **Google Prompt `challenge/dp` (Kiểm tra điện thoại của bạn)**:
   - Trên `challenge/dp`, Google gửi thông báo push trực tiếp tới Samsung S7 (`ce06160685310f1c04` cho M38).
   - Tuyệt đối KHÔNG click "Thử cách khác" (dễ gây nghẽn luồng hoặc khóa tài khoản).
   - **BẪY SUBSTRING URL `challenge` vs `challenge/dp` (CỰC KỲ NGUY HIỂM)**:
     - Google đặt trang nhập password tại: `https://accounts.google.com/v3/signin/challenge/pwd`.
     - Nếu code kiểm tra URL dạng `if "challenge/dp" in url or "challenge" in url:` (hoặc quét `"challenge"` chung chung), code sẽ kích hoạt tap ADB ngay khi vẫn còn ở trang password (`challenge/pwd`), trước khi Google xử lý xong form và trước khi prompt kịp đẩy về máy S7.
     - Lệnh tap trượt vào màn hình trống, sau đó script chuyển sang chờ `myaccount.google.com` và bị timeout.
     - **Quy tắc bắt buộc**: Phải kiểm tra CHÍNH XÁC `"challenge/dp" in cur_url` (hoặc kiểm tra activity `com.google.android.gms/.octarine.ui.OctarineActivity` trên Android qua `dumpsys window windows`). Chờ 1.5 - 2s cho UI dialog render rồi mới tap ADB `540 1362`.
   - **BẪY SCRIPT NGHIÊM TRỌNG**: Trong một số script cũ (như `test_login_m38.py` dòng 811), script lại tự động tìm và click nút *"Thử cách khác"* ngay khi phát hiện `challenge/dp`. Đây là hành vi phản tác dụng làm hủy bỏ prompt push đang chờ duyệt trên điện thoại.
   - Khi Google Prompt xuất hiện trên S7, màn hình hiển thị hộp thoại:
     - Activity hệ thống: `com.google.android.gms/.octarine.ui.OctarineActivity`.
     - Tiêu đề: `"Có phải bạn đang cố khôi phục tài khoản của mình?"` hoặc `"Có phải bạn đang đăng nhập?"`
     - Nút xác nhận chuẩn trên giao diện tiếng Việt S7 là: **`"Vâng, đúng là tôi"`** (bên cạnh `"Không, không cho phép"`).
     - Bounds thực tế trên Samsung S7 (1080x1920):
       - Nút duyệt: `[204,1308][876,1416]` (Tâm: `540, 1362`).
       - Nút từ chối: `[204,1440][876,1548]`.
     - **Bẫy code matcher**: Các script cũ chỉ quét tìm `"Có"`, `"Có, chính là tôi"`, `"Yes"`, nên đã BỎ SÓT nút `"Vâng, đúng là tôi"`, dẫn đến timeout hoặc nhầm tưởng prompt chưa hiện.
     - **Quy tắc bắt buộc cho matcher nút duyệt Prompt**: Phải bao gồm cả `"Vâng, đúng là tôi"`, `"Vâng"`, `"Có"`, `"Có, chính là tôi"`, `"Yes"`, `"Yes, it's me"`, `"Đúng"`.
     - Ngay khi click duyệt trên S7, Google trên trình duyệt GPM sẽ lập tức hoàn tất xác minh và chuyển hướng thẳng vào `https://myaccount.google.com`.

7. **Điều hướng Google Settings trên S7 biến thể Card Layout (MainActivity)**:
   - Khi mở `com.google.android.gms.accountsettings.mg.ui.main.MainActivity`, một số thiết bị S7 hiển thị trang chủ dạng các Card đề xuất ("Đừng để bị mất quyền truy cập...", "Thêm số điện thoại...", "Wallet và gói thuê bao...") khiến tab "Bảo mật" không nằm trong XML màn hình đầu tiên.
   - Xử lý:
     1. Kiểm tra icon Tìm kiếm ở góc trên bên phải (`[804,132][876,204]`, tâm `840, 168`).
     2. Hoặc cuộn ngang trên thanh tab nằm ngay dưới header để làm lộ tab "Bảo mật".
     3. Bấm vào tab "Bảo mật" -> cuộn tìm nút "Mã bảo mật" (Security Code) để lấy mã 10 số.

5. **Đổi tài khoản trong Google Settings trên S7 có nhiều tài khoản (Multi-Account)**:
   - Khi máy S7 có 2-3 tài khoản Google (`dumpsys account`), mục Cài đặt -> Google thường mặc định hiển thị tài khoản đầu tiên (ví dụ `lyphuonganh...` thay vì `caoanh11092003@gmail.com`).
   - Quy trình chuyển đổi tài khoản chuẩn:
     1. Chạm vào header tài khoản đang hiển thị (FrameLayout có content-desc `"Đã đăng nhập bằng tài khoản..."` hoặc bounds chứa email).
     2. Giao diện mở popup chọn tài khoản liệt kê danh sách email.
     3. Dùng ATX XML tìm node có `text` hoặc `content-desc` chứa `target_email` và tap vào.
     4. Sau khi Google Settings chuyển về đúng `target_email`, bấm vào nút `"Tài khoản Google"` (hoặc Quản lý Tài khoản Google) để vào trang quản lý.
     5. Tại trang Quản lý Tài khoản Google, điều hướng đến tab `"Bảo mật"` -> `"Mã bảo mật"` để lấy mã OTP 10 số.

6. **Đường dẫn ADB chuẩn trên host Windows**:
   - `adb` không nằm trong PATH của git-bash terminal. Đường dẫn chuẩn luôn là: `C:\Program Files (x86)\xiaowei\tools\adb.exe` (hoặc `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`). Luôn truyền biến hằng `ADB_EXE` rõ ràng trong mọi script.

8. **Bẫy Xoay Ngang Màn Hình (Landscape Orientation) & Google Settings UI Mới trên S7 (2026-09-06)**:
   - **Bẫy Landscape 1920x1080**: Khi S7 bị bật tự động xoay hoặc kẹt chế độ ngang (`accelerometer_rotation 1`, orientation=2), kích thước hiển thị chuyển thành 1920x1080. Giao diện Google Settings bị chia 2 cột "Đề xuất" / "Tất cả dịch vụ", làm sai lệch toàn bộ tọa độ và ẩn nút điều hướng.
     - **Khắc phục bắt buộc trước khi mở Google Settings**:
       ```bash
       adb -s <serial> shell settings put system accelerometer_rotation 0
       adb -s <serial> shell settings put system user_rotation 0
       ```
   - **Google Settings UI Mới (Nút "Tài khoản Google" ẩn trong Avatar)**:
     - Trên một số bản cập nhật Google Play Services mới, trang chủ Google Settings không hiển thị nút "Tài khoản Google" / "Quản lý Tài khoản Google của bạn" ở màn hình chính.
     - Nút này nằm bên trong dialog popup khi chạm vào header Avatar tài khoản (`[60,758][204,902]`, content-desc `"Đã đăng nhập bằng tài khoản... Tài khoản và các chế độ cài đặt"`).
     - Khi chạm vào Avatar, dialog popup mở ra chứa nút `"Tài khoản Google"` (`[276,648][715,792]`) và danh sách tài khoản chuyển đổi.
     - Nếu cần đổi sang `target_email`: chạm vào email trong danh sách, sau khi trang tải lại với email mới, chạm tiếp vào Avatar một lần nữa để bấm `"Tài khoản Google"` -> tab `"Bảo mật"` -> `"Mã bảo mật"`.
   - **Submit Mã Pin 10 số (challenge/ootp) trên Playwright CDP**:
     - Sau khi điền `pin_inp.fill(code10)`, phím `Enter` có thể không kích hoạt submit. Bắt buộc tìm và click nút rõ ràng:
       ```python
       next_btn = page.locator('button:has-text("Tiếp theo"), button:has-text("Next"), div[role="button"]:has-text("Tiếp theo")')
       if next_btn.count() > 0 and next_btn.first.is_visible():
           next_btn.first.click()
       else:
           page.keyboard.press("Enter")
       ```
     - Nâng timeout vòng lặp xác minh tối thiểu 180s (thay vì 120s) để đủ thời gian giải quyết độ trễ ADB/S7 lock.
   - **Kỷ luật chạy Batch nhiều máy**:
     - Luôn chạy Canary 1 máy (`script.py <mid>`) để nghiệm thu luồng 100% trước khi chạy hàng loạt.
     - Khi chạy batch nhiều máy, tăng timeout lệnh bash (ví dụ 1200s) hoặc chạy tuần tự từng máy theo danh sách để tránh cộng dồn timeout gây dở dang tiến trình.

9. **Ưu Tiên Google Prompt trên Màn Hình Challenge Selection (2026-09-06)**:
   - **Bối cảnh**: Khi Google yêu cầu xác minh 2FA và chuyển hướng tới `https://accounts.google.com/signin/v2/challenge/selection` (hoặc URL chứa `selection`), Google hiển thị danh sách các phương thức xác thực khả dụng.
   - **Quy tắc ưu tiên**:
     1. **Ưu tiên 1 (Google Prompt)**: Click chọn phương thức "Nhấn vào Có trên điện thoại hoặc máy tính bảng" (`div[data-challengetype="6"]`, `li:has-text("Nhấn vào Có")`, `li:has-text("Tap Yes")`). Phương thức này kích hoạt phê duyệt tự động trên S7 qua notification hoặc dialog Octarine mà không cần điều hướng sâu vào Settings.
     2. **Ưu tiên 2 (Mã bảo mật offline)**: Chỉ chọn "Mã bảo mật trên điện thoại" (`div[data-challengetype="8"]`, `li:has-text("mã bảo mật")`, `li:has-text("security code")`) khi KHÔNG có lựa chọn Google Prompt.
   - **Cảnh báo Grouped Notification trên S7**:
     - Khi kiểm tra notification bar (`cmd statusbar expand-notifications`), Samsung S7 có thể gom nhóm thông báo Google Play / Dịch vụ Google Play.
     - Cần phân biệt thông báo cập nhật ứng dụng của CH Play (`com.android.vending: "Có ... bản cập nhật"`) với thông báo đăng nhập thực sự của Google Play Services (`"Bạn đang cố đăng nhập"`, `"Cho phép một ứng dụng truy cập..."`). Tránh tap nhầm vào nút mở rộng của thông báo CH Play.

---

## 10. Bẫy Màn Hình "Nhập mật khẩu gần nhất bạn nhớ", Samsung Pay Overlay & Kỷ Luật Artifact Evidence (User Rule 2026-09-06)

### 1. Bẫy màn hình "Nhập mật khẩu gần nhất bạn nhớ" (Recovery Step 1):
- Khi kích hoạt *"Bạn quên mật khẩu?"*, Google chuyển tới màn hình: *"Khôi phục tài khoản - Nhập mật khẩu gần nhất bạn nhớ là sử dụng với Tài khoản Google này"*.
- Màn hình này **chỉ có 1 ô input mật khẩu duy nhất** (không phải 2 ô đặt lại mật khẩu mới). Các script kiểm tra `p_inputs.count() >= 2` sẽ bị kẹt chờ timeout âm thầm.
- **Giải pháp**: Tại màn hình này, BẮT BUỘC click nút **"Thử cách khác" (Try another way)** (`button:has-text("Thử cách khác"), a:has-text("Thử cách khác")`). Lúc này Google mới chuyển sang các phương án khả thi: Google Prompt gửi về S7, Mã xác minh OTP qua recovery email, hoặc Mã bảo mật 10 số.

### 2. Bẫy Samsung Pay (`com.samsung.android.spay`) Nổi Lên Trên S7:
- Trên một số máy Samsung Galaxy S7 (như Máy 36 `ce10160ac8f1962305`), thao tác vuốt màn hình hoặc đánh thức từ ADB vô tình kích hoạt thanh trượt Samsung Pay (`com.samsung.android.spay`) nổi lên toàn màn hình (`mCurrentFocus=com.samsung.android.spay`).
- Khi Samsung Pay đang nổi, ATX hierarchy dump chỉ thấy giao diện thẻ ngân hàng, hoàn toàn mất dấu Cài đặt Google, khiến hàm `get_s7_security_code` trả về `None`.
- **Khắc phục**: Trước khi mở Cài đặt Google hoặc kéo notification bar, luôn gửi phím Back `adb shell input keyevent 4` để đóng Samsung Pay nếu đang hiển thị.

### 3. Kỷ luật Bắt buộc Gửi Ảnh Đối Soát (`ARTIFACT-EVIDENCE-MANDATORY-GATE`):
- **Phê duyệt bởi Claude Code CLI (06/09/2026)**:
  1. *Script Level*: Mọi script tự động hóa GPM/S7 bắt buộc có khối `finally:` luôn chụp ảnh màn hình tại thời điểm kết thúc và in stdout markers: `SCREENSHOT_SAVED: <path>`, `CURRENT_URL: <url>`, `TASK_STATUS: SUCCESS|FAILED|TIMEOUT`.
  2. *Coordinator Gate*: Coordinator TUYỆT ĐỐI CẤM tin vào text summary tự báo cáo của Worker subagent (Gemini/Claude). Phải kiểm tra file ảnh tồn tại, timestamp <= 60s, chạy OCR/Vision kiểm tra URL thực tế trước khi xác nhận.
  3. *Telegram Media Delivery*: Coordinator BẮT BUỘC gửi ảnh đính kèm `MEDIA:<path>` lên Telegram cho User kiểm tra đối chiếu bằng mắt trước khi kết luận hoàn thành task.

### 4. Bẫy Đa Tài Khoản Trên S7 Lấy Nhầm Mã 10 Số (Case Thực Tế Máy 38):
- **Hiện tượng**: S7 Máy 38 (`ce06160685310f1c04`) đăng nhập 3 tài khoản Google (`truongthuydung...`, `benghowelltpkf1...`, `hoanbui...`). Khi script mở Cài đặt Google, hệ thống mặc định hiển thị tài khoản đầu tiên (`truongthuydung...`). Script tự động vào mục Bảo mật và lấy mã 10 số của `truongthuydung...` nạp cho `benghowelltpkf1@gmail.com`, khiến Google web liên tục báo mã không hợp lệ / mã sai.
- **Khắc phục chuẩn**:
  1. Đọc XML hierarchy kiểm tra email đang hiển thị ở header Google Settings.
  2. Nếu khác `target_email`: chạm vào dropdown/avatar để mở danh sách tài khoản, tìm node chứa `target_email` và tap chọn.
  3. Chờ 2s để màn hình Cài đặt tải lại đúng thông tin của `target_email` rồi mới vào Quản lý tài khoản -> Bảo mật -> Mã bảo mật.

### 5. Thời Hạn Mã Bảo Mật 10 Số (15 Phút) — Tuyệt Đối Không Dùng Lại Mã Cũ:
- Mã bảo mật offline 10 chữ số của Google Play Services chỉ có hiệu lực đúng **15 phút**.
- Nếu script lấy mã từ lượt chạy trước và lưu vào biến / file để chạy lại ở lượt sau, mã sẽ bị hết hạn và Google trả về `challenge/ootp` báo mã sai.
- **Quy tắc**: Bắt buộc trích xuất mã thời gian thực (real-time) ngay trong luồng đăng nhập và submit ngay trong vòng 2-3 phút.

### 6. Modal Xác Nhận "Đổi Mật Khẩu" Sau Khi Nhập 2 Ô Mật Khẩu Mới:
- Trên trang đặt lại mật khẩu của Google, sau khi điền mật khẩu mới vào cả 2 ô (`Passwd` và `ConfirmPasswd`) và nhấn nút Tiếp theo / Lưu mật khẩu, Google hiển thị một **modal xác nhận**:
  *"Bạn sẽ duy trì trạng thái đăng nhập trên thiết bị này: Galaxy S7"* với nút bấm **"Đổi mật khẩu"** (hoặc "Change password").
- Nếu script chỉ nhấn nút Lưu mật khẩu mà không xử lý nút modal xác nhận này, mật khẩu mới sẽ KHÔNG được lưu và trang không chuyển hướng vào `myaccount.google.com`.
- **Selector chuẩn**: `button:has-text("Đổi mật khẩu"), button:has-text("Đổi mật khẩu"), button:has-text("Change password")`. Sau khi click, chờ 3-5s để Google xử lý và điều hướng vào `https://myaccount.google.com/`.




