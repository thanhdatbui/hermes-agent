# Quy trình Warmup Gmail mới Reg bằng Hook ChatGPT trên Android Farm (Samsung S7)

## 1. Bản chất kỹ thuật & Tại sao phải dùng ChatGPT thay Newsletter cũ?
- **Newsletter cũ bị ảo (False Positive):** Các trang newsletter bên thứ ba (Cooperpress, Substack, v.v.) hầu hết đã bật Cloudflare Turnstile bot detection hoặc hàng đợi thư chậm trễ (queue 15-60 phút). Script gửi HTTP POST thuần nhận HTTP 200 thực chất chỉ là trang Cloudflare challenge, không hề có thư thật gửi về hộp thư.
- **Thư nội bộ tự bắn (Internal SMTP) là tự sát:** Dùng 1 email nội bộ gửi hàng loạt đến các Gmail vừa reg kích hoạt bộ lọc "Farm Cluster Inter-linking" của Google AI, dẫn đến chết dây chuyền (Chain Ban).
- **Hook ChatGPT on-device:** 
  - Đăng ký tài khoản OpenAI/ChatGPT trực tiếp qua Google OAuth bằng Chrome trên máy S7 (cùng IP MobiProxy 4G của thiết bị).
  - Ngay khi hoàn tất, Google và OpenAI lập tức gửi **Welcome & Account Data Sharing Security Email** chính thức từ domain corporate về hòm thư Gmail (inbound mail xịn 100%).
  - Tối đa hóa trust của Gmail mới sinh ra, giúp tài khoản sống sót qua 24-48h đầu mà không bị quét đòi SMS.

---

## 2. Quy trình tự động hóa On-Device qua Google OAuth

Module thực thi: `D:/Taadaa/register gmail/scripts/hook_chatgpt_register.py`
Tích hợp trong `gmail_reg_v10.py` tại hàm `persist_success_result(acc, device_id=device_id)`.

### Các bước chuẩn:
1. **Khởi chạy Chrome:**
   `am start -a android.intent.action.VIEW -d 'https://chatgpt.com/auth/login' com.android.chrome`
2. **Xử lý Cookie & Bấm nút Google:**
   - Quét XML popup cookie nếu có -> Tap "Chấp nhận tất cả" (`bounds [78,1608][1002,1716]`).
   - Tap "Tiếp tục với Google" (`bounds [108,660][972,792]`, tâm `540, 726`).
3. **Bỏ qua Dialog Chrome Account:**
   - Chrome trên Android thường bật dialog: *"Đăng nhập vào Chrome... Tiếp tục bằng tài khoản của X / Bỏ qua"*.
   - BẮT BUỘC tap nút **"Bỏ qua"** (`bounds [72,1728][1008,1872]`, tâm `540, 1800`) để đi tiếp vào Google Account Chooser.
4. **Chọn tài khoản / Nhập Email:**
   - Nếu ở `signin/identifier`: Nhập email qua `human_type`, ẩn bàn phím, tap nút "Tiếp theo" (`bounds [675,1722][1008,1776]`).
   - Nếu ở Account Chooser: Tap đúng node chứa email mục tiêu.
5. **Nhập Mật khẩu (Password Challenge):**
   - BẮT BUỘC kiểm tra màn hình `challenge/pwd` trước khi tìm email (tránh tap nhầm email in trên tiêu đề trang).
   - Tap ô mật khẩu (`bounds [78,1158][1002,1314]`).
   - Xóa sạch text cũ bằng keyevent 67.
   - Gõ mật khẩu bằng `human_type(device_id, password)` (xử lý escape ký tự đặc biệt `@`, `#`, `!`).
   - Bấm nút "Tiếp theo" hoặc keyevent 66.
6. **Cấp quyền OAuth (Consent screen):**
   - Màn hình *"Google sẽ cho phép OpenAI truy cập vào thông tin này về bạn"*.
   - Cuộn xuống đáy màn hình: `shell input swipe 540 1500 540 500 300`.
   - Tap nút "Tiếp tục" (`bounds [558,1440][1008,1563]`, tâm `783, 1501`).
7. **Form About You (auth.openai.com/about-you):**
   - Tiêu đề *"Bạn bao nhiêu tuổi?"*.
   - Tính tuổi từ ngày sinh `dob` (nếu không có thì default 24-26).
   - Tap ô tuổi (`bounds [111,1182][969,1254]`, tâm `540, 1218`), gõ số tuổi.
   - Ẩn bàn phím bằng keyevent 4 (Back) hoặc tap header (540, 200).
   - Tap nút "Tiếp tục" của form About you (`bounds [48,1620][1032,1776]`, tâm `540, 1698`).
8. **Nghiệm thu vào thẳng ChatGPT:**
   - Đợi tối đa 30s để WebView render vào `chatgpt.com`.
   - Chụp ảnh màn hình nghiệm thu: `reports/chatgpt_success_<email>.png`.
   - Force stop Chrome và bấm Home (keyevent 3).

---

## 3. Pitfalls & Bài học đắt giá (Anti-False-Positive)

1. **Cấm tuyệt đối False Positive:**
   - Không được phép tự động return `success: True` ở cuối hàm nếu một trong các bước trước đó bị kẹt hoặc trôi vòng lặp.
   - Mỗi bước bắt buộc phải verify chuyển trang thành công (URL hoặc XML text) mới được sang bước sau. Nếu fail -> Trả về `{"success": False, "status": "FAILED_AT_<STEP>"}` kèm ảnh chụp lỗi.
2. **Ký tự đặc biệt trong password:**
   - Ký tự `!` qua ADB shell rất dễ bị bash nuốt hoặc biến thành `\!`. Luôn dùng `human_type` với delay ngẫu nhiên và escape an toàn.
3. **Chạy song song (Parallelism) trên Phone Farm:**
   - Các máy S7 là phần cứng độc lập, dùng các cổng proxy riêng biệt (`test.taadaa.click:51xx`).
   - Khi chạy batch nhiều máy: **BẮT BUỘC dùng `ThreadPoolExecutor(max_workers=N)` chạy song song 100%**.
   - Tuyệt đối không chạy tuần tự từng máy làm lãng phí thời gian nghỉ giữa các ca nuôi TikTok.
