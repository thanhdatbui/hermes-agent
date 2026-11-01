# Kỷ Luật Reg TikTok Lite & Phòng Ngừa Khóc Lóc Thoái Thác (Anti-Whining Protocol)

## 1. Nghiên Cứu Thực Nghiệm: TikTok Lite Trên Dàn Farm ROM Gốc S7 (Android 8.0)
- **Bản APK chuẩn duy nhất toàn farm:** `D:\OneDrive\apk-bank\com_zhiliaoapp_musically_go\tiktok_lite_latest.apk` (v47.6.1). Gói cũ `com.ss.android.ugc.trill.go` đã bị ByteDance bỏ rơi.
- **Rào cản Instant-Ban của Hotmail gõ tay:**
  * Nếu vào thẳng form Đăng ký (`I18nSignUpActivity`) và gõ mail Hotmail thủ công trên máy farm đã cắm sẵn 8 nick TikTok chính -> TikTok quét thấy IP farm + hành vi tạo bot không qua bước xác thực thiết bị -> Kích hoạt Instant-Ban ngay tại giây chọn xong ngày sinh ("Tài khoản của bạn đã bị cấm").
  * **Quy tắc vàng nếu dùng Hotmail:** Bắt buộc đi qua luồng "Đăng nhập" (Log In) ở chân trang trước, nhập mail để TikTok báo "Tài khoản không tồn tại / Bạn chưa có tài khoản? Đăng ký ngay" rồi mới bấm Đăng ký (chiêu thức dương đông kích tây của `social_reg_v1.py` để qua mặt Anti-Fraud).
- **Luồng Google One-Tap SSO (Sống 100%):**
  * Khi máy farm đã có sẵn tài khoản Gmail LIVE trong hệ điều hành Android (đã qua preflight check live), mở TikTok Lite chọn **"Tiếp tục với Google"**.
  * Google Play Services bảo lãnh danh tính thật trên thiết bị -> TikTok cho qua thẳng, không captcha, không đòi OTP, sinh UID sạch vào thẳng Profile.
  * Đã kiểm chứng độc lập trên Máy 78 (`@manhdatquach`) và Máy 76 (`@xuanthuykim`): Cả 2 tài khoản đều HTTP 200 sống khỏe, ngâm tuổi đời song song mà không ảnh hưởng 8 nick chính.
  * **Khả năng đổi mail sau này:** Nick reg qua Google SSO là dạng Linked Account. Sau khi ngâm đủ ngày tuổi, vào Cài đặt đặt Mật khẩu riêng cho TikTok (OTP gửi về Gmail trên máy), sau đó đổi sang Hotmail mới và gỡ liên kết Google hoàn toàn bình thường.

## 2. Preflight Check Live Gmail Bắt Buộc Trước Khi Reg
- Tuyệt đối không bốc Gmail trên máy đi reg khi chưa kiểm tra trạng thái LIVE.
- Một số Gmail reg sau 24h có thể bị Google treo xác minh ("Verify it's you - Confirm you're not a robot" như Máy 205), khiến bước SSO bị kẹt form đòi pass lại.
- Tích hợp kiểm tra tự động qua `check_gmail_live_fast.py` hoặc Google Sign-in probe: chỉ chọn nick có trạng thái `Welcome` mở ô password để reg TikTok Lite.

## 3. Kỷ Luật Hành Động Tuyệt Đối Chống Khóc Lóc (Anti-Whining Protocol)
- **CẤM TUYỆT ĐỐI mở mồm xin lỗi phân trần khi bị Guard chặn:**
  * Những câu văn mẫu: *"Em nhận lỗi sâu sắc", "Em chủ quan nên...", "Em xin lỗi vì..."* bị nghiêm cấm hoàn toàn.
  * User cần kết quả thi công hoặc bằng chứng lỗi thực tế, không cần nghe bot xin lỗi hay kể lể khó khăn.
- **Bản chất của Receipt Guard (Chốt chặn hứa hão):**
  * Hệ thống tự động đóng dấu đỏ `⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]` khi Agent dùng các từ khẳng định như *"Em bắt đầu làm...", "Đã giải quyết xong..."* nhưng trong cùng lượt đó tool call bị Guard chặn hoặc không sinh ra `task_id` thành công.
  * Khi gặp lỗi Guard chặn (hết budget T1, lệnh test bị từ chối): Im lặng đọc đúng lỗi, chuyển đổi sang đúng công cụ được phép (`dispatch_worker`, `unified_patch_pipeline`) để thi công ra diff thật, hoặc chuyển sang L3 BLOCKED kèm evidence cụ thể.
- **Sửa Guard - Không Sửa Worker (O(1) Test Runner Exemption):**
  * Trong `sol_worker.py` và `gemini_web_worker.py`: Bộ lọc an ninh `is_command_safe` bắt buộc cho phép cả `pytest`, `py.test`, `python -m pytest <target> -q`.
  * Khi từ chối lệnh của Worker, Guard bắt buộc phải trả về Actionable Guide (cung cấp cú pháp lệnh mẫu hợp lệ) thay vì chỉ chặn cộc lốc, triệt tiêu 100% bẫy vòng lặp logic (Catch-22) làm Worker bại liệt hết turns.
