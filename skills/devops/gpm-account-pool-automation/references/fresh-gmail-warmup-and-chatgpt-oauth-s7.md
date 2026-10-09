# Fresh Gmail Lifecycle, Warmup Pitfalls & ChatGPT OAuth on Android S7

## 1. Bản chất Fresh Gmail Lifecycle (0h - 48h)
- **Quy tắc bất biến:** Fresh Gmail mới reg trên S7 BẮT BUỘC ngâm $\ge$ 24h - 48h trên máy.
- **Tại sao cấm bật 2FA ngay lúc reg?**
  - Khi tài khoản mới tạo (< 24h), Google kích hoạt cơ chế theo dõi rủi ro cao (*Fresh Account Security Window*).
  - Bật 2FA / nạp số điện thoại / nạp Google Authenticator ngay lập tức sẽ bị Google nghi ngờ bot/chiếm đoạt $\rightarrow$ kích hoạt cờ Checkpoint đòi số điện thoại (SMS Challenge `challenge/iap`), dẫn đến DIE tài khoản ngay lập tức.
  - Sau 24h - 48h ngâm ổn định cùng telemetry của Samsung S7, tài khoản "nguội" thì mới được bật 2FA cuốn chiếu.

## 2. Cạm bẫy Newsletter Warmup tự động
- **False Positive 200 OK của Cloudflare:**
  - Các script dùng HTTP client thuần (`urllib.request`, `requests`) gửi POST lên các endpoint newsletter công khai (như Cooperpress `nodeweekly.com/subscribe`) nhận status 200 OK nhưng thực chất đó là trang HTML thử thách Cloudflare Turnstile ("Just a moment...").
  - Server newsletter **chưa hề nhận được email**, không có bất kỳ thư Inbound nào được gửi về hộp thư.
- **Không ép hòm thư nhận mail ảo hoặc mail nội bộ:**
  - Mail nội bộ từ 1 hòm thư farm (qua SMTP script) gửi đến Gmail mới reg sẽ kích hoạt bộ lọc cụm liên đới (*Cluster Abuse*) của Google AI, dễ làm chết cả chùm.
  - Để tài khoản ngâm tự nhiên cùng duy nhất 1 thư thiết lập ban đầu của Google trên S7 là phương án an toàn nhất.

## 3. Rào cản Google OAuth ChatGPT trên Samsung S7 (Android 8.0)
- **Không dùng App ChatGPT:** App chính thức của OpenAI yêu cầu tối thiểu Android 9.0 (API 28+). Samsung S7 (Android 8.0 / API 26) không cài được app chính thức.
- **Hiện tượng treo OAuth khi tài khoản DIE:**
  - Nếu tài khoản Google đã bị Google đánh cờ DIE (đòi verify số điện thoại): Bấm "Tiếp tục với Google" trên Chrome sẽ bị kẹt vĩnh viễn ở URL `auth.openai.com/api/accounts/authorize?...` với màn hình trắng hoặc treo ở dòng *"Đang chờ auth.openai.com phản hồi..."* vì Google từ chối cấp token phản hồi.
- **Với tài khoản LIVE:**
  - Google nhận diện tài khoản sống, mở mượt mà màn hình nhập Password và xác thực thành công.
  - Tuy nhiên, không thao tác trên máy trong lúc ca cron nuôi TikTok (Row 1..8) đang chạy để tránh xung đột Foreground Window (`com.ss.android.ugc.trill`).

## 4. Quy trình Kiểm tra Live chuẩn (checkmail.live)
- **Cơ chế xác thực bắt buộc:** Site `checkmail.live` yêu cầu phiên đăng nhập (API key) mới cho phép thực hiện check batch.
- **Script chuẩn canonical:** Sử dụng script `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py` (sử dụng Chromium Core 142 + proxy mobi1) để tự động duy trì session, submit batch và phân loại chính xác `LIVE` / `DIE`.
