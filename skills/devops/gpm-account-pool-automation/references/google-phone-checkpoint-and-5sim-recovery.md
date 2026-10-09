# Google Phone Verification Checkpoint & 5sim OTP Guide

## 1. Bản chất Checkpoint Google Phone
- **Check-confirm (Chỉ hỏi số cũ):** Google hiển thị đuôi số (ví dụ: `••41`). Chỉ cần đối soát và nhập đúng số đầy đủ trong hồ sơ gốc (không gửi tin nhắn SMS). Google sẽ nhả ngay.
- **Check-SMS (Bắt buộc nhận mã OTP từ số mới):** Google hiển thị ô nhập số điện thoại bất kỳ để nhận SMS. Chấp nhận số từ các dịch vụ sim ảo như 5sim.
  - *Đặc tính quan trọng:* Ở bước này, Google chỉ mượn số để giải checkpoint tức thời, **hoàn toàn KHÔNG lưu hay gắn số này vào tài khoản** (sau khi vào trong, `myaccount.google.com/phone` vẫn là "Chưa có số điện thoại nào"). Người dùng không cần tốn công xóa số.
- **Rate-limit ("Đã thử quá nhiều lần"):** Nếu Google báo nhập xác minh số nhiều lần hoặc thử thất bại liên tiếp, tài khoản bị tạm khóa bộ đếm rate-limit. Bắt buộc đưa vào danh sách `cooldown_7days` và ngắt kết nối để Google tự reset.

## 2. Quy trình dùng 5sim giải Checkpoint & Bảo toàn tài khoản vĩnh viễn
1. **Thuê số:** Dùng API 5sim (sản phẩm `google`, quốc gia `vietnam` gói `virtual4` hoặc `virtual47`).
   - *Lưu ý:* API trả về số dạng mask (`+848****4846`). Cần bóc số đầy đủ từ giao diện web 5sim đã đăng nhập trên Chrome CDP (`:9222`) tại endpoint `/order/{id}`.
2. **Điền số:** Dùng định dạng đầy đủ quốc tế (ví dụ: `+84888164846`) hoặc local `0888164846` tùy theo form Google.
3. **Chờ OTP:** Poll API `https://5sim.net/v1/user/check/{id}` với timeout tối ưu **150s - 240s** (không để quá ngắn 60s/120s vì SMS thường về ở giây 80-110).
   - Nếu có mã: Điền vào ô `G-______` của Google để hoàn tất login.
   - Nếu hết timeout không có mã: Gọi `cancel/{id}` ngay lập tức để hoàn tiền 100% về ví 5sim.
4. **Bảo mật với 2FA TOTP:**
   - Nếu tài khoản đã có 2FA Authenticator Base32 trong Excel $\rightarrow$ dùng `pyotp.TOTP(secret).now()` giải bước 2FA trước khi qua bước Phone Checkpoint.
   - Nếu tài khoản chưa có 2FA: Sau khi login thành công, vào ngay `myaccount.google.com/signinoptions/twosv` bật **Google Authenticator (2FA TOTP)** và lưu mã Base32 Secret Key vào Excel để lần sau không bao giờ cần SIM nữa.

## 3. Invariant Điều phối Hiện trường & Rủi ro Mất Tiền Oan 5sim
- **QUY TẮC PHÂN LOẠI & BẢO VỆ ACC FARM PHONE (TRÁNH BẪY DEFENSE-BY-EXPLOSION):**
  - **PRE-FLIGHT BẮT BUỘC:** Trước khi tạo profile GPM hay login bất kỳ Gmail nào, PHẢI kiểm tra trường `Số Máy Farm` và `Model Điện Thoại` trong Excel. Nếu `Số Máy Farm != None` (ví dụ: Máy 05, Máy 18, Máy 30...) → tài khoản đó đang thuộc pipeline điện thoại Farm S7.
  - **CẤM TỰ TIỆN BỐC ACC FARM LÀM MẪU TEST:** Tuyệt đối không tự ý bốc acc Farm lên PC để test tính năng hay test mua số. Muốn test phải lấy acc tự do (`Số Máy Farm == None`).
  - **NGHIỆP VỤ MIGRATION / CỨU ACC HỢP LỆ:** Chuyển acc từ Farm S7 lên GPM PC là nghiệp vụ hợp lệ khi máy Farm hỏng, pin chai hoặc User chủ động yêu cầu. Trong trường hợp này, chỉ cần cờ `migration=True` hoặc lệnh trực tiếp từ User là được phép thực hiện, CẤM chặn cứng cực đoan.
  - **NGUYÊN TẮC 'SKIP & ALERT, NEVER CRASH' TRONG BATCH / CRONJOB:**
    - CẤM thiết kế guard ném Exception làm crash toàn bộ batch/cronjob (bẫy *'phòng thủ bằng cách phát nổ'*).
    - **Trong phiên tương tác (Interactive):** Bắt buộc dừng lại hỏi User trước khi mua số tốn tiền hoặc can thiệp acc Farm.
    - **Trong batch / cronjob tự động (Non-interactive):** Nếu gặp acc cần mua số hoặc có xung đột thiết bị, tự động **`SKIP`** acc đó + ghi log/alert và tiếp tục chạy các acc tiếp theo, tuyệt đối không raise exception làm sập cả ca chạy đêm.
  - *Lý do kỹ thuật:* Khi tài khoản chuyển đột ngột từ Farm S7 sang PC, Google kích hoạt Step-up Verification (bắt buộc xác minh thêm SMS dù tài khoản đã có sẵn 2FA TOTP), gây nguy cơ tốn tiền thuê SIM hoặc dính rate-limit.
- **ƯU TIÊN TUYỆT ĐỐI KÊNH GIẢI CỨU 0 ĐỒNG TRƯỚC KHI GỌI 5SIM:**
  - **BƯỚC 1 (miễn phí):** Kiểm tra `Recovery_Email` trong Excel → Nếu có, chọn *"Thử cách khác → Gửi mã về Email khôi phục"* và truy cập mailbox đó để lấy mã.
  - **BƯỚC 2 (miễn phí):** Kiểm tra `2FA_Secret (TOTP)` → Nếu có, dùng `pyotp.TOTP(secret).now()` giải 2FA ngay.
  - **BƯỚC 3 (tốn tiền — chỉ dùng khi đã kiệt cùng):** Mua số 5sim **CHỈ KHI** acc không có Recovery Email, không có TOTP, không thuộc Farm S7.
- **KỶ LUẬT GIAO TIẾP KHI BỊ USER CHỈ TRÍCH:**
  - Khi User bực mình về sai sót: Trả lời ngắn gọn, xác nhận lỗi, báo trạng thái hiện tại. **CẤM** dùng giọng điệu giảng đạo lý, "bài học rút ra", phân tích vòng vo. Người dùng không cần bài học — cần hành động đúng ngay.
- **CẤM TỰ Ý ĐÓNG BROWSER/PROFILE:** Khi mở profile GPM để probe hoặc cứu tài khoản, nếu tài khoản đang dừng ở màn hình đăng nhập, nhập mật khẩu, hay chờ mã xác minh OTP, **TUYỆT ĐỐI CẤM** gọi API `profiles/close` hay `profiles/delete`. Phải giữ nguyên cửa sổ trình duyệt trên màn hình để User có thể trực tiếp quan sát và thao tác nhập mã OTP.
- **RỦI RO MẤT TIỀN OAN TRÊN 5SIM (BÀI HỌC RATE-LIMIT KÉP):**
  - 5sim trừ tiền ngay khi nhận được SMS (không hoàn lại). Nhưng Google sau khi nhận OTP vẫn có thể bật chốt chặn rate-limit: *"Quá nhiều lần thử không thành công. Hãy thử lại sau vài giờ nữa"*.
  - Khi tài khoản vừa bị dính nhiều challenge, session expired hoặc fail captcha liên tiếp, **CẤM mua số 5sim ngay lập tức**. Phải kiểm tra nguy cơ rate-limit trước; nếu có dấu hiệu rate-limit thì ngâm tài khoản ít nhất 24h - 48h, không mua OTP để tránh mất tiền vô ích.
  - **Quy tắc thử tối đa:** Thử tối đa 1-2 lần trên 1 tài khoản; nếu thất bại hoặc dính lỗi rate-limit của Google phải lập tức dừng lại, đưa vào cooldown và báo cáo minh bạch cho User, tuyệt đối không retry mù mịt.
- **CHÍNH SÁCH BẢO TỒN PROFILE GPM KHI GMAIL DIE:**
  - CẤM TUYỆT ĐỐI gọi API `profiles/delete` xóa profile GPM khi Gmail có trạng thái `DIE`. Các profile này lưu cookie/session OpenAI/Codex đã ver số tốn tiền, vẫn có thể đăng nhập độc lập.
  - Sổ cái `master_gmail_manager.xlsx`: Phải lưu toàn bộ acc DIE sang sheet riêng `Gmail_DIE_Archive` (kèm cột `ChatGPT_Reg` và giữ nguyên SDT cũ, pass, recovery), không được xóa bỏ dữ liệu gốc.
- **AN TOÀN ĐỒNG BỘ FILE EXCEL & QUAN SÁT TELEMETRY:**
  - Bắt buộc dùng `_EXCEL_SYNC_LOCK = threading.Lock()` khi nhiều luồng cập nhật song song `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`.
  - Luôn phát structured telemetry metric dạng JSON `[TELEMETRY_METRIC]` đo `duration_ms` và trạng thái `success/failed` cho các thao tác đồng bộ nhạy cảm.
  - Giữ lại `logging.StreamHandler(sys.stdout)` trong `basicConfig` để quan sát realtime qua console/terminal.

## 4. Đọc số điện thoại đầy đủ (unmasked) từ 5sim Web khi API trả về mask
API 5sim v1 trả về số dạng mask (`+848****4846`) trong response của `buy/activation` và `check`. Để lấy số đầy đủ không bị che:
1. Mở Chrome CDP đã đăng nhập sẵn vào 5sim (thường ở port `:9222` — là Chrome Hermes).
2. Điều hướng tới `https://5sim.net/order/{order_id}` ngay sau khi mua.
3. Quét DOM tìm element chứa chuỗi `+84` có độ dài 11-15 ký tự:
```python
for t in p_chrome.locator("button, span, div, p").all_inner_texts():
    t_clean = t.replace("\n", "").replace(" ", "").strip()
    if "+84" in t_clean and 11 <= len(t_clean) <= 15:
        full_phone = t_clean
        break
```
4. Điền số đầy đủ vào form Google (định dạng `+84xxxxxxxxx` hoặc `0xxxxxxxxx`).

**Lưu ý:** Phải làm bước này ngay sau khi mua, trước khi timeout order hết hạn (~15 phút).
