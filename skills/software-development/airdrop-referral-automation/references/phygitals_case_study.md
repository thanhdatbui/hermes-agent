# Phygitals Case Study: Privy Auth & AppsFlyer OneLink Attribution

## 1. Trích xuất trọn vẹn Share Payload qua Native Share Intent
- Khi bấm "Invite friends" trên UI, app không chỉ lưu vào clipboard mà còn bắn Intent `android.intent.action.SEND`.
- Hệ thống Android mở màn hình Messaging (`com.samsung.android.messaging`).
- OCR đọc được chuỗi tin nhắn gốc:
  ```text
  Join me on Phygitals and we'll both get $1 in Pack Credits! Use my code 384b8cfef9f0 or tap my link: https://phygitals.onelink.me/lHmK/7xx2rdv6
  ```
- Kỹ thuật này giúp lấy được cả mã mời chuẩn xác lẫn link đầy đủ trước khi bị rút gọn `...` trên UI app.

## 2. Điểm nghẽn OneLink 404 (Application ID not found) và Cạm bẫy OCR
- Khi OCR đọc từ ảnh màn hình hoặc tin nhắn chia sẻ:
  Chuỗi template ID `1HmK` (số 1 đứng đầu) bị nhận dạng nhầm thành chữ `lHmK` (chữ L thường).
- Khi gọi URL nhầm: `https://phygitals.onelink.me/lHmK/7xx2rdv6`
  ```http
  HTTP/1.1 404 Not Found
  Application ID not found
  ```
- Khi sửa lại đúng template ID chuẩn với số 1: `https://phygitals.onelink.me/1HmK/7xx2rdv6`
  Server AppsFlyer trả về HTTP 200 kèm kịch bản chuyển hướng Intent Android hoàn hảo:
  ```javascript
  var app_link = 'phygitals://?af_android_url=https%3A%2F%2Fphygitals.com&af_channel=join&af_deeplink=true&af_dp=phygitals%3A%2F%2F&af_referrer_customer_id=did%3Aprivy%3Acmuwu8mmg036f0bld74c1ey57&af_referrer_uid=...&af_siteid=com.phygitals.mobile&campaign=join_share&deep_link_sub1=384b8cfef9f0&deep_link_value=join&media_source=af_app_invites&onelink_id=1HmK&shortlink=7xx2rdv6&source_caller=sdk';
  ```
- **Bài học xương máu:** Tuyệt đối không tin 100% vào OCR với các ký tự phân giải mập mờ (`1` vs `l`, `0` vs `O`) trong URL shortlink của AppsFlyer / Branch.io. Bắt buộc đối chiếu chuỗi intent hoặc brute-force hoán đổi ký tự trước khi kết luận link lỗi.

## 3. Phân cấp giải pháp trích xuất OTP: Graph Token Pool vs On-Device App Fallback
- **Tier 1 (Tối ưu nhất & Phục vụ Scale Song Song): Microsoft Graph API Token Pool**:
  - Không cần máy phải cài hay đăng nhập app Outlook. Bất kỳ máy Android nào trong farm (75+ máy) cũng có thể dùng bất kỳ Hotmail nào từ kho 244+ tài khoản có Graph Refresh Token (`gmail_clean_v2.xlsx`).
  - Gửi request HTTP trực tiếp lấy OTP qua REST API (`/mailFolders/inbox/messages` và `junkemail`) chỉ mất 1-2 giây, O(1), không bị lỗi xoay màn hình, popup modal chào mừng hay treo ứng dụng.
  - Cho phép chạy song song đa worker (`ThreadPoolExecutor(max_workers=4..8)`), mỗi worker gán 1 máy rảnh với 1 mail trong pool.
  - **Cạm bẫy URL Encoding trong OData Graph API**: Nếu truyền tham số sắp xếp có khoảng trắng trần (`$orderby=receivedDateTime desc`), Python `urllib` sẽ báo lỗi `http.client.InvalidURL`. Bắt buộc encode thành `$orderby=receivedDateTime%20desc` hoặc bỏ `$orderby` để tránh lỗi ngầm nuốt OTP.
- **Tier 2: Gmail IMAP SSL (`imap.gmail.com:993`)**: Privy gửi email từ `no-reply@mail.privy.io`, thư về Inbox trong 2-4 giây, trích xuất regex `\b\d{6}\b` thành công 100% qua App Password.
- **Tier 3 (Dự phòng khi không có Token/App Password): On-Device Outlook Fallback**:
  - Khi tài khoản mục tiêu chưa có token hoặc token bị thu hồi, tận dụng tài khoản Hotmail đang có session live trong app `com.microsoft.office.outlook` trên thiết bị.
  - Lưu ý: Thư OTP luôn nằm trong tab "Khác" (Other), cần tap chuyển tab (`x=374, y=314`) và đóng các popup consent/ghi chú tài khoản trước khi OCR.
- **Cảnh báo Kỷ luật (Chống kết luận ẩu không có bằng chứng ảnh)**:
  CẤM TUYỆT ĐỐI agent chỉ dựa vào kết quả script API rỗng để kết luận "không nhận được mail" hoặc "hệ thống bị chặn" mà không kiểm tra thực tế. Mọi kết luận về lỗi hộp thư bắt buộc phải có visual evidence (ảnh chụp màn hình app mail).

## 4. Kỹ thuật nhập OTP 6 số vào ô chia tách của Privy (Split Boxes)
- Privy sử dụng 6 ô nhập mã pin riêng rẽ. Nếu dùng bàn phím số ảo Samsung keypad tap toạ độ đôi khi bị miss hoặc không ăn focus.
- Sử dụng lệnh Android KeyEvent loop:
  `for d in 7 1 1 6 1 0; do input keyevent KEYCODE_$d; sleep 0.2; done`
  Phương pháp này kích hoạt trực tiếp event `onKeyPress` của React Native TextInput, điền chuẩn 100% qua 6 ô và tự động submit sang màn hình Onboarding/Packs.

## 5. Cấu trúc Suite Airdrop Automation
Kho mã nguồn đặt tại `D:/Taadaa/airdrop-automation`:
- `core/adb_operator.py`: Điều khiển thiết bị và bàn phím số Samsung Keypad.
- `core/otp_receiver.py`: Bộ đọc OTP tự động.
- `runners/phygitals_ref_runner.py`: Script runner khép kín từng thiết bị.

## 6. Phân tích Khác biệt Nền tảng iOS vs Android & Bài học Ref $0.00 / Pending
- **Hiện tượng thực tế**:
  - Trên các máy Android (Máy 11, Máy 12, Máy 3), app Phygitals ghi nhận attribution thành công 100% trong tab Rewards (`@FairyCommander9341 referred you` / `You joined with their invite on Oct 7`).
  - Trên acc chính (Máy 4), chỉ số thống kê trong tab Rewards đã ghi nhận: **`3 Invited`**, **`$0 Earned`** và trạng thái **`Pending`**.
- **Giải mã từ mã nguồn Bundle & Đối chiếu thực tế trên màn hình**:
  1. Phygitals áp dụng cơ chế "Give $1, Get $1 in Pack Credits" dùng làm voucher mở thẻ (Rip Packs), không phải tiền mặt rút ngay.
  2. Mã mời có cấu trúc 12 ký tự hex (ví dụ: `384b8cfef9f0`, `cc6032017780`).
  3. **Phân định cơ chế nhập Code trên Android (Acc chính vs Acc phụ clean)**:
     - **Trước khi đăng ký (Fresh install)**: Không có ô nhập code tay. Phải đi qua OneLink AppsFlyer (`https://phygitals.onelink.me/...`) để gán attribution tự động.
     - **Tài khoản chính (Established / Referrer Account)**: Khối `HAVE A REFERRAL CODE?` bị backend ẩn hoàn toàn trên giao diện Rewards (chỉ hiển thị `Give $1, Get $1`, thống kê Invited/Pending và link mời riêng).
     - **Tài khoản phụ mới tinh (Clean / No-ref registration)**: CÓ ô nhập code tay nằm ở **đáy màn hình tab Rewards** (`HAVE A REFERRAL CODE? [Enter code] [Apply]`).
       - **Cạm bẫy nhập ký tự qua ADB trên Samsung Keypad**: Bộ gõ có thể tự ghép ký tự/gợi ý số (ví dụ `cc6032017780` biến thành `cc60320177801`). Bắt buộc tap ra ngoài vùng input (unfocus) để commit text sạch và kiểm tra qua OCR/crop trước khi bấm Apply.
       - **Phản hồi từ Backend khi bấm Apply**: App trả về thông báo dưới nút Apply:
         `"We couldn't verify your code right now — it's saved and we'll retry automatically."`
         Mã được lưu vào queue retry phía máy chủ; tiền không được cộng tức thì ($0.00) và không hiện `@... referred you` như OneLink.
     - **Tính bất biến của người bảo trợ**: Nếu máy phụ đã gán người bảo trợ từ trước (qua OneLink), việc nhập code của người khác vào ô này và bấm Apply sẽ bị hệ thống bỏ qua, không thể ghi đè.
     - **Kết luận kiến trúc**: OneLink Intent là kênh attribution duy nhất đạt độ tin cậy tuyệt đối và cập nhật tức thì vào bảng thống kê của tài khoản chính (`X Invited`).
  4. **Trạng thái Thưởng Pending**:
     - Khoản thưởng $1 Pack Credits được hệ thống giữ ở trạng thái **Pending** để chống gian lận farm ảo (Sybil protection).
     - Điều kiện để chuyển từ Pending sang Available credit thường yêu cầu tài khoản mới hoàn tất các bước Onboarding (chọn sở thích, mở demo pack) hoặc có giao dịch đầu tiên / duyệt theo chu kỳ batch của hệ thống.
- **Kinh nghiệm điều phối**: Khi phát hiện dấu hiệu lệch thưởng giữa hai hệ điều hành hoặc phần thưởng ở trạng thái Pending, phải dừng việc chạy dồn dập trên farm Android và đề xuất người dùng đối chứng trên thiết bị iOS thật.
