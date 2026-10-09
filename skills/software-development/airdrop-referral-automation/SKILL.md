---
name: airdrop-referral-automation
description: Automate Web3 airdrops, ref links, Privy & OTP on Android.
tags: [airdrop, referral, android, web3, otp, appsflyer, privy]
---

# Airdrop & Referral Automation Suite

Kỹ năng điều phối, tự động hóa quy trình cày Referral, Airdrop Web3 và Testnet/Mainnet đa tài khoản trên dàn máy thật Android Phone Farm.

---

## 1. Trích xuất OneLink / Deep-Link từ Android Clipboard (Không dùng Logcat)
Nhiều ứng dụng Web3/Airdrop (React Native, Flutter) khi bấm "Copy Link / Share" không hiển thị text link trên giao diện mà ghi ngầm vào Android clipboard.
Lệnh `service call clipboard 1` trên Android 7/8 trả về Parcel thô rất khó giải mã. 

### Kỹ thuật Paste & Read qua Trình duyệt:
1. Mở Samsung Browser / Chrome vào trang trắng:
   ```bash
   adb -s <SERIAL> shell am start -a android.intent.action.VIEW -d "about:blank" -p com.sec.android.app.sbrowser
   ```
2. Tap vào thanh URL (`x=429, y=149` trên màn S7 1080x1920).
3. Gửi keyevent Paste: `adb -s <SERIAL> shell input keyevent 279`
4. Chụp ảnh màn hình và chạy WinRT OCR đọc chuỗi URL OneLink / Invite link chính xác 100%.

### Kỹ thuật trích xuất trọn vẹn qua Native Share Sheet:
Nhiều app khi bấm "Invite Friends / Share" sẽ kích hoạt `android.intent.action.SEND` mở ứng dụng Tin nhắn (Messages) hoặc bộ chia sẻ hệ thống:
1. Tap vào nút "Invite Friends" / "Share".
2. Chụp màn hình khung soạn thảo tin nhắn / share sheet.
3. OCR sẽ đọc được toàn văn mẫu tin nhắn mời (bao gồm cả invite code tường minh lẫn link OneLink đầy đủ trước khi bị rút gọn `...` trên UI app).

---

## 2. Xử lý OTP & Bàn phím số (Privy Auth Web3)
Các app sử dụng hạ tầng ví nhúng như Privy Auth thường gửi OTP 6 số và khóa bàn phím ở chế độ numeric keypad cố định.

### Bảng toạ độ bàn phím số Samsung (SM-G930F 1080x1920):
```python
SAMSUNG_KEYPAD_COORDS = {
    "1": (140, 1266), "2": (410, 1266), "3": (672, 1266),
    "4": (147, 1444), "5": (411, 1444), "6": (672, 1444),
    "7": (146, 1620), "8": (409, 1620), "9": (672, 1620),
    "0": (409, 1800),
}
```

### Xử lý Popup Consent & Màn hình Chào Outlook trên Android:
Khi mở app Microsoft Outlook trên máy farm, nếu tài khoản lâu ngày không mở sẽ hiện modal "Ghi chú nhanh về tài khoản Microsoft của bạn / Bạn đang nắm quyền kiểm soát":
- Xử lý nhanh không để kẹt: Gửi chuỗi dismiss popup:
  ```bash
  # Tap nút OK nếu ở dạng ngang (landscape) hoặc cuộn xuống tap OK ở dạng dọc
  adb -s <SERIAL> shell input tap 961 866
  adb -s <SERIAL> shell "input swipe 500 1500 500 500 300 && sleep 0.5 && input tap 541 1706"
  ```

### Chiến lược lắng nghe hộp thư & Phân cấp Mail (Mail Extraction Hierarchy):
- **Tier 1 (Ưu tiên số 1 - Headless Microsoft Graph API Token Pool)**:
  - **Nguyên lý Tách rời Máy & Tài khoản (Decoupled Device-Account Architecture)**: KHÔNG phụ thuộc vào việc máy farm có cài hay đăng nhập app Outlook hay không. Bất kỳ máy Android nào cũng có thể nhận bất kỳ Hotmail nào từ kho token!
  - **Khai thác kho tài khoản**: Tận dụng kho tài khoản Hotmail đã lưu sẵn Graph Refresh Token + Client ID (như `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` với 240+ tài khoản).
  - **Cơ chế**: Script backend tự exchange refresh token lấy `access_token` tại `https://login.microsoftonline.com/consumers/oauth2/v2.0/token`, sau đó truy vấn trực tiếp REST API `https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages` và `junkemail`.
  - **Cạm bẫy OData query space trong Python urllib (Bug ngầm nuốt OTP)**:
    Khi gọi URL `.../messages?$top=5&$orderby=receivedDateTime desc`, nếu để khoảng trắng trần `receivedDateTime desc` thì `urllib.request.urlopen` sẽ ném ngoại lệ `http.client.InvalidURL: URL can't contain control characters`. Nếu bị bọc trong `except Exception: pass`, lỗi này sẽ bị nuốt im lặng khiến script báo không nhận được mail! BẮT BUỘC dùng URL encode `$orderby=receivedDateTime%20desc` hoặc bỏ hẳn `$orderby` (mặc định Inbox đã sắp xếp theo thời gian mới nhất).
  - **Ưu điểm vượt trội**: Nhận OTP trong 1-2 giây, O(1), không lo đơ app, xoay màn hình, hay bị vướng modal chào của Microsoft. Giúp scale song song 4-8 máy cùng lúc cực kỳ mượt mà.
- **Tier 2: Gmail IMAP SSL (`imap.gmail.com:993`)**: Nhận mã OTP chỉ trong 3-5 giây qua App Password, độ tin cậy tuyệt đối với các dịch vụ Auth Web3 (Privy, Dynamic, Web3Auth).
- **Tier 3: On-Device Mailbox Fallback (Trích xuất tại chỗ qua App Outlook/Gmail trên thiết bị)**:
  - **CHỈ DÙNG LÀM FALLBACK** khi tài khoản mục tiêu không có Graph Token hoặc token bị revoke.
  - **Cạm bẫy Hotmail/Outlook Tab "Khác" (Focused vs Other / Non-focused inbox)**:
    Thư OTP từ các dịch vụ Auth Web3 (như Privy `no-reply@mail.privy.io`, Dynamic, Turnkey) khi gửi về Hotmail **100% bị thuật toán Microsoft phân loại vào tab "Khác" (Other)**, hoàn toàn KHÔNG xuất hiện ở tab "Ưu tiên" (Focused).
    - Nếu kiểm tra bằng mắt ở tab mặc định, hộp thư trông sẽ như trống trơn, dẫn đến phán đoán sai lầm rằng "mail bị chặn từ vòng ngoài".
    - **Quy tắc bất biến (Anti-Assumption & Visual Evidence Invariant):** CẤM TUYỆT ĐỐI kết luận "hộp thư không có OTP" hoặc "Microsoft chặn mail" nếu chỉ chạy script API/IMAP! Bắt buộc phải mở app Outlook trên máy thật, tap vào tab "Khác" (`x=374, y=314` trên S7), chụp ảnh gửi `MEDIA:<path>` chứng minh tận mắt trước khi báo cáo.
  - **Quy trình fallback qua app Outlook**:
    1. Lấy địa chỉ mail đang đăng nhập sẵn trong app Outlook (tap `x=100, y=160` mở drawer Outlook) để điền vào ô Auth.
    2. Gửi OTP -> ADB chuyển nhanh sang app Outlook (`monkey -p com.microsoft.office.outlook -c android.intent.category.LAUNCHER 1`).
    3. Đóng popup modal nếu có -> chuyển tab "Khác" -> OCR đọc OTP từ preview thư mới nhất -> chuyển về app airdrop điền OTP.

### Kỹ thuật nhập OTP 6 số trên ô Pin-Code rời rạc (Privy Split Input Boxes):
Các ô nhập OTP của Privy (6 ô vuông rời rạc) thường không nhận `input text` thông thường nếu chưa focus chuẩn, hoặc bàn phím số che khuất:
- Giải pháp chuẩn xác 100%: Gửi trực tiếp chuỗi keyevent số Android vào hệ thống:
  ```bash
  adb -s <SERIAL> shell "for d in <D1> <D2> <D3> <D4> <D5> <D6>; do input keyevent KEYCODE_\$d; sleep 0.4; done"
  ```
  **Lưu ý thời gian trễ (Timing Under Load):** Trên Samsung S7 khi chạy đa luồng hoặc máy tải nặng, nếu để `sleep 0.2` rất dễ bị nuốt mất số (ví dụ `3 7 0 7 1 1` bị rơi `0` và `1` thành `3 7 7 1`). BẮT BUỘC dùng `sleep 0.4s` giữa các chữ số để hệ thống React Native kịp trigger `onKeyPress` từng ô.

---

## 3. Reverse Engineering React Native Bundle & Preflight Check OneLink
1. **Kiểm tra liveness của OneLink trước khi phân bổ máy:**
   - Trước khi lock máy và nạp mail chạy ref, luôn chạy curl kiểm tra header OneLink:
     ```bash
     curl -sL -A "Mozilla/5.0 (Linux; Android 10; Mobile) Chrome/116.0" "<ONELINK_URL>"
     ```
   - **Cạm bẫy OCR nhầm lẫn ký tự số `1` / chữ `l` / `I`, số `0` / chữ `O`:**
     Trong mã template OneLink (ví dụ template ID `1HmK` rất hay bị WinRT OCR đọc nhầm thành chữ `lHmK`), server AppsFlyer sẽ trả về `404 Application ID not found`.
     CẤM TUYỆT ĐỐI vội vàng kết luận link chết hoặc dev config sai template! Bắt buộc hoán đổi kiểm tra các cặp ký tự dễ nhầm lẫn (`1` ↔ `l`, `0` ↔ `O`) hoặc trích xuất chuỗi thô từ clipboard/intent log trước khi đưa ra nhận định.
   - Khi gọi đúng OneLink sống, server AppsFlyer trả về HTML chứa metadata attribution đầy đủ (`af_dp=phygitals://`, `deep_link_sub1=<CODE>`, `campaign=join_share`).
2. **Xác định cơ chế nhập Code:**
   - Kéo APK về máy: `adb pull /data/app/<package>-*/base.apk`
   - Đọc `assets/index.android.bundle`: tìm kiếm `Have a referral code?`, `Promo code`, `Redeem`. Nếu không có form nhập code riêng trong Profile/Settings, toàn bộ hệ thống ref 100% phụ thuộc vào OneLink attribution.

---

## 4. Kỷ luật Khóa Thiết bị Farm & Multi-Worker Parallel Pool
- **CẤM TUYỆT ĐỐI thao tác trên máy farm mà chưa Acquire Device Lock:**
  Trước khi mở app, cài đặt APK hay chạy bất kỳ lệnh ADB nào trên máy farm, Coordinator BẮT BUỘC phải khởi động daemon khóa thiết bị:
  ```bash
  python D:/Taadaa/tools/device_lock_keeper.py start --machine <N> --project "airdrop automation" --ttl 120
  ```
  Nếu không lock máy ngay từ bước 0, các tiến trình cron định kỳ của farm (nuôi nick TikTok, feed session) sẽ tự động chiếm quyền điều khiển và cướp app giữa chừng gây hỏng luồng automation.
- Luôn kiểm tra trạng thái rảnh trước khi chọn máy: `python D:/Taadaa/tools/device_lock_keeper.py status --machine <N>`.

### Quy tắc Điều phối Đa Worker Song Song (Parallel Multi-Worker Invariant):
- Khi scale quy trình ref trên dàn farm (nhiều máy), **CẤM TUYỆT ĐỐI chạy tuần tự (sequential loop)** từng máy một gây nghẽn tiến độ hàng giờ.
- Mỗi máy chạy đúng 1 account độc lập. BẮT BUỘC tổ chức luồng song song qua `ThreadPoolExecutor(max_workers=4..8)` hoặc worker script riêng biệt:
  - Mỗi worker tự độc lập acquire lock máy mình.
  - Tự tải/cài đặt và inject deep-link OneLink.
  - Tự chuyển sang app mail trên máy đó để lấy OTP.
  - Tự chụp ảnh xác nhận và giải phóng lock khi hoàn tất.

### Quy tắc Mapping Tài khoản Đúng Máy (Strict Per-Machine Account Binding):
- Khi chỉ thị yêu cầu "dùng đúng mail của máy đó": BẮT BUỘC tra cứu cột `số máy` (Cột A) trong `gmail_clean_v2.xlsx` để lấy đúng tài khoản gán cố định cho thiết bị đó.
- CẤM TUYỆT ĐỐI lấy ngẫu nhiên tài khoản của máy này gán sang máy khác chạy ref, gây xáo trộn database quản lý và làm mất đồng bộ session của farm.

### Khảo sát Phân biệt Nền tảng iOS vs Android & Bẫy Chặn Thưởng Ảo (Platform Bias & Sybil Defense):
- **Hiện tượng Attribution Đã Nhận Nhưng Số Dư $0.00:**
  Nhiều ứng dụng Web3/Airdrop ghi nhận thành công attribution qua OneLink (màn hình hiển thị rõ `@User referred you` / `You joined with their invite`), nhưng cả tài khoản chính và phụ đều giữ nguyên `$0.00 Pack Credits / Rewards`.
- **Cơ chế chống Farm / Sybil Gate ngầm:**
  1. **Yêu cầu iOS First:** Một số dự án chỉ tự động credit ngay cho người dùng iOS (xác thực phần cứng qua Apple DeviceCheck / App Attest), trong khi trên Android bị giữ lại hoặc chặn do không vượt qua Google Play Integrity / thiếu SIM thực.
  2. **Yêu cầu First Action (Hành động kích hoạt):** Khoản thưởng $1 Pack Credits là voucher mở pack, hệ thống backend thường yêu cầu tài khoản mới hoàn thành Onboarding (chọn sở thích, mở demo pack) hoặc có giao dịch đầu tiên mới giải ngân.
- **Kỷ luật Dừng Kịp Thời (Fail-Fast & Device Cross-Check):**
  Khi chạy thử nghiệm 2-3 máy Android đều ghi nhận attribution thành công nhưng số dư không nhảy, BẮT BUỘC DỪNG ngay việc chạy hàng loạt toàn farm. Báo cáo đối chứng với thiết bị iOS thật để xác nhận chính sách trước khi mở rộng quy mô.

### Phân tích Cơ chế Ô Nhập Code Ref: Pre-reg vs Post-reg (Fresh vs Registered UI Divergence):
Khi cộng đồng hoặc User hỏi về "phần nhập mã giới thiệu thủ công (Enter referral code)": CẤM vội vàng kết luận "app không có ô nhập code"! Bắt buộc phân định 3 trạng thái:
1. **Trước khi đăng ký (Fresh install / Pre-registration)**:
   - Màn hình chào mừng và form Auth (Privy email/phone) **HOÀN TOÀN KHÔNG CÓ ô nhập code**.
   - Mọi cơ chế gán ref trước đăng ký 100% phụ thuộc vào AppsFlyer OneLink Intent (`https://phygitals.onelink.me/...`).
2. **Tài khoản chính (Đã có mã mời / Referrer Account)**:
   - Backend tự động **ẨN HOÀN TOÀN** khối `HAVE A REFERRAL CODE?` ở đáy tab Rewards. Acc chính không thể nhập mã của người khác.
3. **Tài khoản phụ mới tinh đăng ký chay (Clean Account / Chưa qua link ref)**:
   - **CÓ Ô NHẬP CODE TAY**, nằm ở **đáy màn hình tab Rewards** (cuộn qua hết Invite Link và thống kê xuống dưới cùng):
     ```text
     HAVE A REFERRAL CODE?
     [ Enter code ]     [ Apply ]
     ```
   - *Hạn chế & Phản hồi Backend khi nhập code tay*:
     - **Bẫy Autocomplete Samsung Keypad khi nhập qua ADB**: Khi dùng `adb shell input text`, bàn phím mặc định Samsung có thể kích hoạt inline prediction/gợi ý từ, làm biến dạng mã (ví dụ `cc6032017780` bị thêm số thành `cc60320177801`).
     - **Giải pháp chuyển IME sang AdbKeyboard triệt tiêu lỗi ghép chữ**:
       Tạm thời chuyển sang bàn phím ADB trước khi nhập text:
       ```bash
       adb -s <SERIAL> shell ime set com.github.uiautomator/.AdbKeyboard
       adb -s <SERIAL> shell "input text <CODE>"
       # Sau khi hoàn tất và verify OCR, chuyển lại bàn phím gốc:
       adb -s <SERIAL> shell ime set com.sec.android.inputmethod/.SamsungKeypad
       ```
     - **Quy trình nhập text sạch O(1) nếu vẫn dùng Samsung Keypad**: Tap ô input -> Xóa trắng bằng keyevent 67 loop -> Gõ mã qua `input text` -> **BẮT BUỘC tap phím Hoàn tất (Done) tại `(988, 1812)` hoặc tap ra khoảng trống ngoài ô (unfocus)** để đóng bàn phím và commit text sạch -> Chụp ảnh/OCR kiểm tra đúng chuỗi trước khi tap `Apply`.
     - **Bẫy HTTP Proxy Chết trên Máy Farm Chặn Kết Nối Privy Auth**:
       Nhiều máy farm còn giữ thiết lập `http_proxy` nội bộ (`192.168.110.2:20008`) từ các batch nuôi TikTok/Farm cũ nhưng proxy đã rớt. Khi mở Privy đăng nhập email sẽ báo ngay `Something went wrong. Please try again` (logcat: `[CIO] Connection failed`).
       * Kiểm tra nhanh: `adb -s <SERIAL> shell "settings get global http_proxy"`
       * Khắc phục O(1): Xóa proxy rác đưa về mạng trực tiếp: `adb -s <SERIAL> shell "settings put global http_proxy :0"`.
     - **Phản hồi Backend thực tế**: Khi nhập mã hợp lệ và bấm `Apply`, hệ thống trả về thông báo:
       `"We couldn't verify your code right now — it's saved and we'll retry automatically."`
       App **không cộng tiền ngay ($0.00)** và không hiển thị người bảo trợ ngay lập tức, mà lưu mã vào hàng đợi retry trên backend.
     - **Kỷ luật Cung cấp Bằng chứng Lỗi Nhập Mã (Toast/Inline Text Crop)**:
       Thông báo từ chối / retry của backend app Web3 thường hiển thị dưới dạng inline label chữ nhỏ màu xám/vàng bên dưới nút Apply. Khi gửi ảnh `MEDIA:` báo cáo kết quả, **BẮT BUỘC crop cận cảnh khối input + message lỗi**, CẤM chỉ gửi ảnh full-screen dài khiến chữ lỗi bị nén mờ gây hiểu lầm là ảnh chụp không đúng thời điểm.
4. **Quy tắc khoá bảo trợ (Referral Immutability)**: Nếu tài khoản đã được gán người giới thiệu qua OneLink từ trước (hiển thị `@Referrer referred you`), việc gõ mã người khác vào ô này và bấm Apply sẽ bị hệ thống bỏ qua, không thể ghi đè.
3. **Trạng thái Thưởng: Pending vs Instant Earned**:
   - Khi ref thành công, tài khoản chính ghi nhận số lượng mời tăng lên (ví dụ `3 Invited`), nhưng phần tiền có thể hiển thị `$0 Earned` và nằm ở trạng thái **`Pending`**.
   - Điều này xác nhận ref đã ăn vào hệ thống backend, nhưng phần thưởng $1 Pack Credits được giữ ở chế độ chờ duyệt (Pending) cho đến khi tài khoản được ref phát sinh hành động kích hoạt (mở demo pack/onboarding/first purchase) hoặc qua đợt batch credit của sàn.

### Quy tắc Bằng chứng Thị giác Hòm thư (Mailbox Evidence Invariant — Chống Báo Mồm Khiến User Bỏ Quên):
- CẤM TUYỆT ĐỐI agent chỉ dựa vào script API/IMAP trả về rỗng để báo mồm "không có thư OTP", "mail không về", "bị Microsoft chặn" mà không gửi ảnh chụp màn hình chứng minh!
- Việc báo mồm không có ảnh sẽ làm User tưởng thật, đưa ra quyết định sai lầm và bỏ quên hiện trường.
- **Tiêu chuẩn bắt buộc**: Trước khi kết luận hộp thư không có mã, BẮT BUỘC phải mở app mail trên thiết bị thật, kiểm tra cả tab "Ưu tiên" (Focused) lẫn tab "Khác" (Other), chụp ảnh màn hình, soi qua vision và đính kèm `MEDIA:<path>` trong tin nhắn báo cáo.

---

## 5. Tài liệu tham khảo & Case Study thực chiến
- Chi tiết case study phân tích Phygitals, OneLink 404 và xử lý Privy OTP: xem `references/phygitals_case_study.md`.
- Mã nguồn bộ runner tự động hóa: đặt tại `D:/Taadaa/airdrop-automation`.
