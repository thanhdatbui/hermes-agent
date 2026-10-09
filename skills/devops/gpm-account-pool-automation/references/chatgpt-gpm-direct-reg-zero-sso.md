# Direct ChatGPT Registration on GPM (Zero-SSO Invariant)

## 1. Bối cảnh & Bản chất kỹ thuật
- **Vấn đề với Google SSO ("Continue with Google"):**
  Khi một tài khoản Gmail được reg trên S7 (dạng lách số / bypass phone) đăng nhập lên GPM PC và lập tức gọi Google SSO sang dịch vụ bên thứ ba (OpenAI), Google kích hoạt luồng đánh giá rủi ro chéo (cross-site security evaluation). Hậu quả: reCAPTCHA bão, IP bị hạ nhiệt, và Google nâng mức phạt lên **SMS Checkpoint cưỡng chế**, làm chết oan tài khoản.
- **Bản chất Direct Email + Password:**
  Khi đăng ký tài khoản ChatGPT trực tiếp bằng Email + Password thông thường:
  + OpenAI gửi email xác minh OTP 6 số về hộp thư.
  + Với Google, đây thuần túy là hành vi **nhận email thông thường**, hoàn toàn không kích hoạt cơ chế bảo vệ danh tính hay rào cản SSO.
  + Mức độ an toàn đạt **100%**, bảo vệ vĩnh viễn tài khoản Google gốc.

## 2. Zero-SSO Invariant & Phân vai kiến trúc
- **Google SSO:** CHỈ dùng cho Google Cloud Platform / Antigravity OAuth.
- **ChatGPT Web / Codex:** TUYỆT ĐỐI dùng Direct Email + Password signup.
- **Phân vai 2 luồng:**
  + *Luồng A (S7 Android):* Hook reg ChatGPT cho các Gmail **MỚI VỪA REG** trên điện thoại S7 (`watchdog_link_chatgpt_idle.py` / `hook_chatgpt_register.py`).
  + *Luồng B (GPM PC):* Chạy script chuyên trách `chatgpt_gpm_direct_reg.py` đăng ký bù ChatGPT cho **TOÀN BỘ DÀN GMAIL CŨ** đã có profile sống trên GPM.

## 3. Quy trình thực thi 8 bước trên GPM
1. **Khởi động Profile GPM:** Gọi Local API `GET /api/v3/profiles/start/{id}` lấy `remote_debugging_address`, chạy trên đúng cổng proxy Mobi 4G của máy.
2. **Kiểm tra phiên sống sẵn có:** Mở `https://chatgpt.com/`. Nếu không còn nút Login/Sign up -> Đã có session, đánh dấu `CHATGPT_READY` và hoàn tất.
3. **Mở trang Đăng ký:** Điều hướng tới `https://chatgpt.com/auth/signup`. Tuyệt đối bỏ qua mọi nút Google SSO.
4. **Điền thông tin xác thực:**
   - Điền Email từ danh sách.
   - Điền Mật khẩu: Đọc từ Cột 3 Excel `master_gmail_manager.xlsx`. Nếu `< 12` ký tự, tự động chuẩn hóa bằng hậu tố `@Taadaa2026` để đáp ứng chính sách OpenAI.
5. **Bốc OTP tự động từ tab Gmail:**
   - Mở tab phụ (`context.new_page()`) tới `https://mail.google.com/mail/u/0/#inbox`.
   - Polling 15 lần (mỗi lần 4s) tìm email từ `ChatGPT` hoặc `OpenAI`. BẮT BUỘC click vào hàng thư để mở rộng chi tiết nội dung.
   - Trích xuất mã OTP 6 số: Lấy phần tử CUỐI CÙNG `nums[-1]` trong `re.findall(r"\b(\d{6})\b", text)` để tránh bốc nhầm mã cũ ở đầu luồng hội thoại (thread).
   - Đóng tab Gmail an toàn, quay lại tab ChatGPT điền mã.
6. **Hoàn tất Onboarding (About You):**
   - Điền Họ & Tên hợp lệ.
   - Điền Ngày sinh (DOB) đảm bảo tuổi $\ge 20$.
   - Bấm Continue tiến vào màn hình chat chính.

## 4. CLI Runner & Unit Tests
- Script thực thi: `D:/Taadaa/GPM auto/scripts/chatgpt_gpm_direct_reg.py`
  ```bash
  # Chạy thử nghiệm không mở browser (kiểm tra candidate & password)
  python "D:/Taadaa/GPM auto/scripts/chatgpt_gpm_direct_reg.py" --dry-run --limit 3

  # Chạy canary cho 1 account cụ thể
  python "D:/Taadaa/GPM auto/scripts/chatgpt_gpm_direct_reg.py" --email example@gmail.com
  ```
- Test suite: `D:/Taadaa/GPM auto/tests/test_chatgpt_gpm_direct_reg.py`
  ```bash
  pytest "D:/Taadaa/GPM auto/tests/test_chatgpt_gpm_direct_reg.py"
  ```

## 5. Pitfalls Thực Tế & Hard Gates Chống Báo Cáo Sai (Learnings 2026-09-25)
1. **Thương hiệu email gửi về là "ChatGPT" chứ không phải "OpenAI":**
   - Tiêu đề thư thường là: `ChatGPT — Mã của bạn cho ChatGPT ...` hoặc `Mã xác minh tạm thời của bạn` (`Your temporary ChatGPT verification code is ...`).
   - Nếu script chỉ tìm `tr:has-text("OpenAI")` sẽ bị miss và timeout. Bắt buộc tìm cả `ChatGPT` lẫn `OpenAI`.
2. **Bẫy Gmail Threading (Luồng tin nhắn) & Regex OTP:**
   - Khi OpenAI gửi nhiều lần xác nhận, Gmail tự động gom vào 1 thread duy nhất.
   - Dùng `nums[0]` sẽ lấy mã OTP cũ hết hạn từ đầu thread $\rightarrow$ dẫn đến lỗi *"Mã không chính xác"*.
   - **Bắt buộc dùng `nums[-1]`** (mã mới nhất ở cuối thread) và cuộn xuống đáy email (`window.scrollTo(0, document.body.scrollHeight)`).
3. **Hard Gate xác minh lỗi OTP & False-Positive Prevention:**
   - Sau khi điền OTP, script BẮT BUỘC kiểm tra các từ khóa lỗi: *"Mã không chính xác"*, *"Incorrect code"*, *"Invalid code"*, *"Too many attempts"*.
   - Nếu gặp lỗi: LẬP TỨC chụp ảnh `step6_otp_error.png`, unmark cờ Excel, trả về `FAIL_WRONG_OTP`. CẤM TUYỆT ĐỐI ghi nhận thành công.
   - Chỉ được công nhận `SUCCESS` khi URL thuộc domain `chatgpt.com` (không còn `/auth/`) và ô chat `#prompt-textarea` hiển thị sẵn sàng.
4. **Bẫy Account Picker ("Chào mừng trở lại / Chọn tài khoản"):**
   - Với các profile đã từng đăng nhập trước đó, OpenAI có thể hiển thị modal popup: *"Chào mừng trở lại - Chọn một tài khoản để tiếp tục"*.
   - Modal này che khuất khung chat phía sau. Script cần click trực tiếp vào nút tài khoản `button:has-text("{email}")` để bypass modal và vào thẳng giao diện chat.
5. **Kỷ luật Concurrency Login GPM:**
   - Khi chạy watchdog login GPM (`post_evening_gpm_login_watchdog.py`), cho phép chạy 5 workers (`MAX_WORKERS = 5`) nhưng bắt buộc giữ vững invariant: **khác port proxy và khác số máy**, kèm `stagger 5s`.
6. **Bẫy Khách Ẩn Danh (Anonymous Visitors) & Cookie Consent Banner của ChatGPT:**
   - ChatGPT hiện nay cho phép khách chưa đăng nhập (anonymous users) vẫn thấy giao diện chat, thanh sidebar và ô nhập `#prompt-textarea` để gõ prompt!
   - Nếu script chỉ kiểm tra sự tồn tại của `#prompt-textarea` hoặc text "Đoạn chat mới", nó sẽ nhận diện nhầm khách ẩn danh là "ĐÃ ĐĂNG NHẬP" (`ALREADY_LOGGED_IN`)!
   - **Quy tắc bất biến (Negative Auth Gate):**
     Nếu trên giao diện còn xuất hiện nút `[Đăng nhập]` (`button:has-text("Đăng nhập")`, `button:has-text("Log in")`) hoặc `[Đăng ký miễn phí]` (`button:has-text("Sign up")`, `button:has-text("Đăng ký")`) $\rightarrow$ **100% LÀ CHƯA ĐĂNG NHẬP!**
     Đồng thời, trang thường có banner Cookie Consent (*"Chúng tôi sử dụng cookie"* / *"Chấp nhận tất cả"*). Script phải chủ động click *"Chấp nhận tất cả"* để giải phóng DOM trước khi tương tác.
   - Chỉ được công nhận `ALREADY_LOGGED_IN` khi:
     1. KHÔNG CÒN bất kỳ nút Đăng nhập / Đăng ký nào.
     2. CÓ element User Profile (`[data-testid="profile-button"]`, avatar hoặc tên người dùng ở góc trái dưới).
7. **Kỹ thuật WinRT OCR soi bằng chứng độc lập (Gate 6 Invariant):**
   - Không bao giờ tin tưởng mù quáng vào log hay status trả về của script automation.
   - Sử dụng công cụ `python scripts/winrt_ocr.py <path_to_screenshot>` để đọc lại chữ thực tế trên màn hình chụp. OCR độc lập là "máy phát hiện nói dối" bắt đứng các lỗi: OTP sai, tài khoản ẩn danh, popup che khuất mà Playwright locator bắt nhầm.
8. **OpenAI Direct Signup Flow Variation (OTP First):**
   - OpenAI có thể linh hoạt thay đổi thứ tự form: thay vì Email $\rightarrow$ Password $\rightarrow$ OTP, OpenAI thường chuyển thẳng từ Email $\rightarrow$ OTP verification $\rightarrow$ sau đó mới thiết lập Password & About You. Script direct reg cần xử lý cả 2 biến thể (kiểm tra xem trang đang ở `password` field hay `otp` input box).
9. **Xử lý Rollback Cờ Excel khi Fix False-Positive:**
   - Khi phát hiện một tài khoản bị cắm cờ `CHATGPT_READY` do lỗi nhận diện khách ẩn danh của logic cũ, bắt buộc rollback xóa bỏ chuỗi `| CHATGPT_READY` trong Cột 14 của `master_gmail_manager.xlsx` trước khi re-run canary hoặc đưa vào batch chạy lại.
10. **Candidate Selection Invariant: Ưu tiên Profile Nuôi Ấm (Warm Nurtured Accounts) Tránh Google Re-Auth/Captcha:**
   - *Bẫy:* Quét tuần tự GPM DB (`SELECT Id, Name FROM Profiles ORDER BY Id ASC`) sẽ vướng vào các profile "nguội" đã ngâm lâu ngày không mở, khiến Google bắt "Xác minh danh tính của bạn" và đòi reCAPTCHA khi truy cập `mail.google.com`.
   - *Giải pháp:* Trong `get_gpm_candidates()`, bắt buộc đối soát với `gpm_gmail_nurture_state.json`. Gán **Priority 1** cho các tài khoản có `status == "success"` (đã được cron nuôi lướt YouTube/Google trơn tru gần nhất). Những profile này mở Gmail vào thẳng Inbox 100% không bao giờ gặp captcha hay đòi login lại.
11. **Xử lý Re-login & Checkbox reCAPTCHA Google (Khi Cứu Phiên Profile Nguội):**
   - Khi Google hiển thị *"Xác minh danh tính của bạn"* kèm *"Xác nhận bạn không phải là rô-bốt"*:
     1. Quét các frame tìm anchor reCAPTCHA (`"recaptcha" in f.url and "anchor" in f.url`).
     2. Click checkbox `#recaptcha-anchor` / `.recaptcha-checkbox`.
     3. Bấm `[Tiếp theo]` (`#identifierNext` / `#passwordNext`).
     4. Nếu hiện ô mật khẩu, tự động điền `pwd` từ Excel và submit để tiến vào Inbox lấy OTP OpenAI.
     5. Nếu reCAPTCHA chuyển sang audio/image challenge phức tạp: Dừng lại ngay (Freeze) để tránh Google kích hoạt SMS checkpoint theo đúng Invariant an toàn farm.
12. **Phân Biệt Giữa Kiểm Thử Luồng "Reg Bằng Mã OTP" vs "Session SSO Còn Sót" (Tránh False Verification):**
   - *Bẫy & Phản hồi từ User:* Khi user chỉ đạo "chạy canary reg ChatGPT bằng mã", việc bốc các profile GPM đã có sẵn session ChatGPT từ trước (thường do batch Google SSO cũ lưu lại cookie) rồi báo cáo `ALREADY_LOGGED_IN` là **sai lệch mục tiêu kiểm thử (False Verification)**. User sẽ phản ứng ngay: *"Ủa t bảo reg = mã chứ k log qua sso mà"*.
   - *Quy tắc kiểm thử:* Để kiểm thử luồng đăng ký bằng mã OTP (Direct Email Signup), bắt buộc phải chọn profile thỏa mãn 2 điều kiện:
     (a) Trên `chatgpt.com` CHƯA TỪNG ĐĂNG KÝ (chưa có session cookie, mở ra form đăng ký/đăng nhập trắng).
     (b) Hộp thư `mail.google.com` sống khỏe và vào thẳng Inbox (đã được nuôi ấm) để sẵn sàng bốc mã xác minh.
   - Bắt buộc phải exercise trọn vẹn luồng thật: Điền Email $\rightarrow$ OpenAI gửi mã $\rightarrow$ Mở tab Gmail bốc mã 6 số $\rightarrow$ Nhập mã OTP vào OpenAI $\rightarrow$ Điền Password / About You $\rightarrow$ Điều hướng vào màn hình chat chính.
13. **Bẫy Bốc Nhầm Số Ngẫu Nhiên Trong Gmail & Cơ Chế Tìm Kiếm Toàn Cục `from:openai.com OR ChatGPT`:**
   - *Bẫy trích xuất:* Trong Gmail, ngoài thư OpenAI còn có email chào mừng Google ("Get started with Gmail...", "1-15 trong số 15", các số ngày tháng). Nếu thư OpenAI rơi vào tab khác (*Promotions*, *Social*, *Updates*) hoặc nằm sâu dưới danh sách, regex `\b(\d{6})\b` quét mù trên `body.inner_text()` có thể bốc phải các chuỗi số của hệ thống Google $\rightarrow$ Nhập vào OpenAI bị báo *"Mã không chính xác"*.
   - *Giải pháp tìm kiếm toàn cục:* Khi tab Gmail mở ra, tự động gõ vào ô Search (`input[name="q"]`): `from:openai.com OR ChatGPT` rồi nhấn `Enter`. Điều này gom toàn bộ thư của OpenAI về một màn hình duy nhất, lọc bỏ 100% email rác của Google.
   - *Kỹ thuật mở thư Desktop:* Dùng `target_row.click(force=True)` kết hợp `target_row.press("Enter")`. Phím Enter trên Gmail web luôn kích hoạt mở toàn màn hình chi tiết bức thư.
   - *Vị trí mã OTP chuẩn:* Chờ selector `div[role="main"] div.ii.gt` render xong, trích xuất mã 6 số từ các thẻ tiêu đề in đậm font lớn (`h1, h2, strong, b`) nằm ngay dưới dòng *"Your temporary ChatGPT verification code is:"*.
14. **Hard Gate Bắt Buộc Sau Khi Điền OTP (Chống Tự Ý Báo Cáo Xong):**
   - Không bao giờ cho phép script coi việc nhập mã OTP là kết thúc luồng. Sau khi submit OTP, script bắt buộc phải kiểm tra thông báo lỗi ("Mã không chính xác", "Incorrect code"). Nếu có lỗi, lập tức dừng lại, chụp ảnh báo cáo và hủy cờ Excel. Chỉ khi trình duyệt điều hướng thực sự vào trang chat (`chatgpt.com` không có `/auth/`) và ô `#prompt-textarea` sẵn sàng thì mới được coi là thành công.
15. **Cờ Bắt Buộc `--otp-only` & Khóa Chặt Nhánh Early Return:**
   - Khi chạy kiểm thử hoặc batch reg tài khoản mới bằng OTP, script BẮT BUỘC hỗ trợ cờ `--otp-only`.
   - Khi `--otp-only` được bật: Tuyệt đối KHÔNG chạy nhánh `if is_chatgpt_logged_in -> return ALREADY_LOGGED_IN` và KHÔNG chạy nhánh `if "already exists" -> return ALREADY_EXISTS`. Ép trình duyệt đi tiếp vào luồng form đăng ký Email → Bốc OTP từ Gmail → Điền OTP → Tạo mật khẩu → About You.
16. **Bẫy Snippet Regex Toàn Trang vs Deep Email Inspection:**
   - CẤM TUYỆT ĐỐI dùng regex tìm 6 số trên `body.inner_text()` của trang danh sách thư (snippet scan), kể cả khi dùng regex `(?:code is|mã là|verification code)\s*(\d{6})`. Lý do: khi thư OpenAI chưa về, các email bảo mật của Google ("Việc thêm số điện thoại...", "1-15 trong số 15") vẫn có thể chứa chuỗi số khiến regex bắt nhầm (như bắt nhầm mã `445495` trên `tachau`), làm OpenAI báo "Mã không chính xác" và kích hoạt rate limit.
   - BẮT BUỘC: Chỉ trích xuất mã OTP khi đã mở đúng hàng thư của OpenAI/ChatGPT vào giao diện chi tiết (`div[role="main"] div.ii.gt`).
17. **Cơ Chế Lọc Ứng Viên 100% Chưa Từng Đăng Ký (Zero ChatGPT Cookies):**
   - Để tìm đúng tài khoản cần reg bằng mã mà không bị dính session cũ hay dính Google captcha:
     1. Đọc `gpm_gmail_nurture_state.json`: lấy các email có `status == 'success'` (đã nuôi ấm).
     2. Kiểm tra file SQLite `Cookies` của profile GPM:
        - Bắt buộc có $\ge 2$ Google cookies (`SID, SSID, HSID, SAPISID`) để đảm bảo session Gmail sống 100%.
        - Bắt buộc có **0 ChatGPT/OpenAI cookies** (`host_key LIKE '%chatgpt.com%' OR host_key LIKE '%openai.com%' == 0`) để đảm bảo profile chưa từng đăng nhập hay đăng ký ChatGPT trước đó.
18. **Pitfall Worker Timeout Trong MSYS2/Windows Terminal Khi Chạy Browser Automation:**
   - Khi điều phối worker subagent chạy lệnh automation trình duyệt (như Playwright/GPM) vốn cần 2–4 phút để hoàn tất chu trình bốc OTP:
     - Terminal mặc định có timeout 180s. Nếu subagent gọi lệnh mà không chỉ định timeout cao hơn (ví dụ `timeout=240` hoặc `300`), terminal sẽ ngắt giữa chừng khiến subagent bị kẹt và cạn budget 600s của delegation.
     - Coordinator BẮT BUỘC ghi rõ timeout trong prompt dispatch: `terminal(..., timeout=240)`.
19. **Bẫy `tr role="tablist"` Trong Gmail Web Desktop (Playwright Selector Collision):**
   - *Triệu chứng:* Khi dùng locator tổng quát `tr:has-text("ChatGPT")` để click hàng thư trong Gmail, Playwright báo lỗi:
     `Locator.click: Element is not visible waiting for locator("tr:has-text(...)").first locator resolved to <tr role="tablist" class="aAA J-KU-Jg J-KU-Jg-K9">…</tr>`.
   - *Nguyên nhân:* Gmail đặt thanh phân loại danh mục tab (Chính / Xã hội / Quảng cáo) bên trong một thẻ `<tr role="tablist">` ở đầu danh sách. Thẻ `<tr>` này che khuất hoặc vô hình, khiến Playwright bắt nhầm tab bar thay vì hàng thư thật.
   - *Khắc phục chuẩn xác:* BẮT BUỘC dùng selector chuyên biệt cho hàng thư thực sự trong Gmail web:
     `tr.zA:has-text("ChatGPT"), tr.zA:has-text("OpenAI"), tr[role="row"]:has-text("ChatGPT"), tr[role="row"]:has-text("OpenAI")` (class `zA` là định danh chính thức của hàng email trong Gmail DOM), và click trực tiếp vào subject span:
     `target_row.locator('span.bog, td.xY, span[data-thread-id]').first.click(force=True)`.
20. **Bẫy Form OpenAI "About you" Đổi Từ Ngày Sinh (Birthdate) Sang Ô Tuổi (Age):**
   - *Triệu chứng:* Sau khi nhập mã OTP thành công, script điền xong Full name nhưng kẹt lại ở `https://auth.openai.com/about-you` và fail Hard Gate 2. WinRT OCR đọc màn hình hiện thông báo đỏ: *"How old are you? ... Enter a valid age to continue"*.
   - *Nguyên nhân:* Giao diện OpenAI hiện tại không còn dùng ô chọn ngày tháng năm sinh (`input[name="birthdate"], input[type="date"]`) mà yêu cầu nhập trực tiếp số tuổi vào ô **`Age`** (`input[name="age"], input#age, input[type="number"]`). Script cũ chỉ tìm `dob_inp` nên để trống ô Age, khiến OpenAI chặn không cho bấm `[Continue]`.
   - *Khắc phục chuẩn xác:* Trong bước 8 Onboarding, bắt buộc định vị và điền ô Age:
     `age_inp = page.locator('input[name="age"], input#age, input[type="number"], input[placeholder*="Age"], input[inputmode="numeric"]').first` $\rightarrow$ `age_inp.fill("25")`, kết hợp fallback `dob_inp` nếu có form cũ.
21. **Bẫy Modal Popup Onboarding "You're all set" Che Khuất Ô Chat (`chatgpt.com` Hard Gate 2):**
   - *Triệu chứng:* Sau khi điền xong "About you" (Tên & Tuổi), trình duyệt chuyển hướng thành công sang URL `https://chatgpt.com/` nhưng script vẫn báo `HARD GATE 2 FAIL: Không vào được chatgpt.com với ô prompt textarea! URL hiện tại: https://chatgpt.com/`.
   - *Nguyên nhân (WinRT OCR soi màn hình):* OpenAI hiển thị modal chào mừng đầu tiên:
     *"You're all set - ChatGPT can make mistakes. Chats may be reviewed and used for training. Learn more - [Continue]"*.
     Vòng lặp dismiss popup cũ chỉ tìm `["Bắt đầu", "Tiếp tục", "Let's go", "Okay, let's go", "Next", "Done", "Đóng"]` và **THIẾU nút `"Continue"`** (tiếng Anh). Do đó popup không được đóng, che khuất giao diện chat chính và làm Playwright timeout khi chờ `#prompt-textarea`.
   - *Khắc phục chuẩn xác:*
     1. Bổ sung `"Continue"` vào danh sách dismiss button:
        `for b_text in ["Continue", "Bắt đầu", "Tiếp tục", "Let's go", "Okay, let's go", "Next", "Done", "Đóng"]:`
        tìm `button:has-text("{b_text}"), [role="button"]:has-text("{b_text}")`.
     2. Mở rộng selector prompt textarea:
        `#prompt-textarea, textarea[placeholder*="ChatGPT"], textarea[placeholder*="nhắn"], textarea, div#prompt-textarea, div[contenteditable="true"]`.
22. **Kỷ Luật Kế Thừa Workflow Từ S7 Sang GPM (Cấm Mò Mẫm / Tái Phát Minh Khi S7 Đã Có Code Mẫu Chuẩn):**
   - *Phản hồi từ User:* *"ủa cái này có script ở s7 r, thì mày áp dụng y workflow ở đó mà làm thôi, sao mệt thế nhỉ"*.
   - *Nguyên tắc cốt lõi:* Khi tự động hóa một dịch vụ web trên GPM (như ChatGPT, Google, Hotmail) mà Farm đã có script chạy ổn định trên S7 (`D:/Taadaa/register gmail/scripts/hook_chatgpt_register.py`), BẮT BUỘC mở file script S7 lên đọc và kế thừa 100% logic trước khi code trên GPM.
   - *Lý do:* OpenAI và các nền tảng web lớn dùng chung backend auth và giao diện web responsive giữa Mobile và Desktop. Mọi màn hình, form fields, và onboarding popups trên S7 đều xuất hiện y hệt trên PC:
     1. Bước "About You": S7 đã có sẵn logic điền Họ tên + Tính tuổi (`calculate_age_from_dob` điền `str(age) = 25/26`).
     2. Bước Onboarding: S7 đã có sẵn danh sách bắt các modal `"You're all set"`, `"Bạn đã hoàn tất"`, `"Làm quen với Giọng nói"`, `"Get started with Voice"` và bấm `"Continue" / "Tiếp tục" / "Bỏ qua"`.
     3. Nhận diện hoàn tất: S7 đã định nghĩa bộ chỉ báo thoát auth vào chat (`"Free", "Welcome to ChatGPT", "Trò chuyện", "Khung chat"`).
   - *Hành vi cần tránh:* Không bao giờ ngồi đoán mò hoặc thử sai (trial-and-error) lại từ đầu các trường form hay popup trên PC khi trong kho vũ khí của Farm (`register gmail`, `automation-core`) đã có sẵn lời giải chuẩn được kiểm nghiệm trên 160 máy S7.
23. **Giới Hạn Gmail-Only Của `chatgpt_gpm_direct_reg.py` & Quy Tắc Khóa Cứng (Blocked Contract) Cho Hotmail / Multi-Provider / Exact Profile ID:**
   - *Thực trạng mã nguồn:* Script canonical `chatgpt_gpm_direct_reg.py` hiện tại được thiết kế chuyên biệt và cứng (hardcoded) cho Gmail:
     1. CLI parser chỉ có `--email`, `--limit`, `--dry-run`, `--otp-only`. Hoàn toàn không có tham số `--profile-id` để target chính xác profile ID.
     2. Candidate discovery dùng regex `([a-zA-Z0-9_.+-]+@gmail\.com)`, tự động bỏ qua mọi domain khác (như `@hotmail.com`, `@outlook.com`).
     3. Nguồn mật khẩu `get_password_for_email()` gắn cứng với `master_gmail_manager.xlsx` / `gmail_clean_v2.xlsx`, không đọc `D:\Taadaa\Hotmail\hotmail_input.txt`.
     4. Luồng bốc OTP mở cứng URL `https://mail.google.com/mail/u/0/#inbox` và dùng DOM selector của Gmail (`tr.zA`, `div.ii.gt`). Đối với profile Hotmail/Outlook (đang xác thực với Microsoft Account), việc mở Gmail sẽ vướng màn hình đăng nhập Google và timeout (`FAIL_OTP_TIMEOUT`).
   - *Kỷ luật an toàn tuyệt đối:* Khi nhận yêu cầu đăng ký ChatGPT cho các profile Hotmail hoặc non-Gmail:
     - CẤM TUYỆT ĐỐI bịa đặt kết quả thành công, không tạo profile thay thế hoặc bypass an toàn.
     - Dừng lại ngay (BLOCKED) và xuất trình bằng chứng file/line cùng Contract tối thiểu:
       + CLI: Bổ sung `--profile-id <id>` để target trực tiếp không qua heuristic discovery.
       + Resolver: Thêm resolver đọc credentials từ `D:\Taadaa\Hotmail\hotmail_input.txt` (`email|password|recovery_email|refresh_token`).
       + OTP Provider: Tách lớp OTP thành provider trừu tượng: `MicrosoftGraphOTPProvider` (dùng refresh token gọi Graph API lấy thư không cần mở tab trình duyệt) hoặc `OutlookWebOTPProvider` (mở `outlook.live.com`).



