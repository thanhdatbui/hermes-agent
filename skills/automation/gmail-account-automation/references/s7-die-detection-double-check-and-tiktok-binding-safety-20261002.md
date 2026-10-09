# Quy Tắc Xác Minh Gmail DIE Chuẩn & Khóa An Toàn TikTok Trên S7 (02/10/2026)

## 1. Bản chất vấn đề & Chỉ đạo của Operator
- **Chỉ đạo dứt khoát:** *"K acc đã die thì đc phép xoá. Vậy vấn đề là do nó logic check live ngu"*.
- **Nguyên tắc vận hành:**
  1. Tài khoản đã **DIE THẬT** thì **HOÀN TOÀN ĐƯỢC PHÉP XÓA** khỏi máy S7 để giải phóng slot (tối đa 5 tài khoản Google/máy) phục vụ reg tài khoản mới. Không cần đợi đồng bộ lên GPM đối với acc đã chết.
  2. Tuy nhiên, việc xóa phải dựa trên **bằng chứng DIE xác thực tuyệt đối**, không được để logic check live cẩu thả phán bừa làm xóa oan tài khoản đang sống.

## 2. Phân tích sự cố xóa nhầm Gmail Máy 3 (28/09/2026)
- **Hiện trường:** Gmail `an.nhuan.work64541@gmail.com` được tạo ngày 08/09/2026 trên Máy 3 (UID 13). Đến 15:53 ngày 28/09/2026, script `preflight_s7_rolling_cleanup.py` chạy trước ca reg chiều, gọi `checkmail.live` quét danh sách tài khoản.
- **Hạt sạn logic:**
  + `checkmail.live` là dịch vụ web bên thứ ba. Khi IP bị Google rate-limit hoặc Google trả về reCAPTCHA người máy, web trả về nhãn `[DIE]`.
  + Script `preflight_s7_rolling_cleanup.py` chỉ đặt timeout 30s và đọc kết quả 1 lần duy nhất:
    ```python
    if status == "DIE":
        return {"action": "REMOVE", "target_email": acc_name}
    ```
  + Không có bước kiểm tra chéo (double-check), script lập tức phát lệnh ADB xóa sạch tài khoản khỏi Cài đặt S7 trong 36 giây.
  + Đến 16:07, script reg tài khoản mới `chi.tieu.eyww770@gmail.com` đè vào slot trống.
  + **Hậu quả:** Tài khoản `an.nhuan` thực tế vẫn sống 100%, có mật khẩu và 2FA đầy đủ, nhưng bị xóa mất khỏi app Gmail của Máy 3. Khi tài khoản TikTok `annhubvqttr` (slot 24) gặp sự cố đăng nhập cần nhận OTP email, máy hoàn toàn không nhận được thư, dẫn đến lỗi hệ thống kéo dài.

## 3. Quy trình 2 Tầng Xác Minh (Double Verification Gate) bắt buộc trước khi xóa acc DIE
Trước khi kết luận một tài khoản là `DIE` và phát lệnh `remove_account_adb`, script bắt buộc phải đi qua 2 tầng:

### Tầng 1: Quét sơ bộ (Batch Filter)
- Dùng `checkmail.live` hoặc API check live nhanh để lọc nhanh các tài khoản chắc chắn `LIVE`.
- Nếu Tầng 1 trả về `DIE`, `DISABLED`, hoặc `UNREGISTERED` -> **CẤM XÓA NGAY LẬP TỨC**. Chuyển sang Tầng 2 để thẩm định độc lập.

### Tầng 2: Thẩm định trực tiếp qua Google Sign-In Endpoint (Definitive Gate)
- Điều hướng trực tiếp tới endpoint nhận diện của Google: `https://accounts.google.com/signin/v2/identifier?hl=vi` (qua proxy của chính thiết bị đó hoặc residential proxy sạch).
- Điền email mục tiêu và bấm Tiếp tục.
- **Chỉ kết luận DIE THẬT khi xuất hiện đúng 1 trong 2 thông báo chính thức từ Google DOM:**
  1. *"Không tìm thấy tài khoản Google của bạn"* / *"Couldn't find your Google Account"* (Unregistered/Deleted).
  2. *"Tài khoản của bạn đã bị vô hiệu hóa"* / *"Your account has been disabled"* (Disabled).
- **Các trường hợp KHÔNG ĐƯỢC COI LÀ DIE:**
  - Google yêu cầu giải reCAPTCHA người máy (`challenge/recaptcha`).
  - Google yêu cầu xác minh số điện thoại hoặc thiết bị (`challenge/iap` / Phone Checkpoint).
  - Lỗi mạng, Timeout, Proxy error, hoặc HTTP 429/5xx.
  👉 Các trường hợp này là **Transient / Live Checkpoint**, tài khoản **VẪN CÒN SỐNG**, tuyệt đối cấm xóa!

## 4. Khóa An Toàn Liên Kết TikTok (TikTok Binding Gate)
Đây là cổng an toàn bắt buộc để tránh "giết nhầm" email đang nuôi TikTok:
1. **Kiểm tra chéo Workbook TikTok:**
   - Trước khi xóa bất kỳ tài khoản Google nào trên máy $M$ (dù đã xác nhận DIE ở Tầng 2), script bắt buộc phải tra cứu cột F (`GMAIL`) và cột A (`MÁY`) trong `taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`.
2. **Quy tắc xử lý:**
   - Nếu email đó **ĐANG LIÊN KẾT VỚI MỘT NICK TIKTOK TRÊN MÁY $M$**:
     + **TUYỆT ĐỐI CẤM TỰ ĐỘNG XÓA.**
     + Việc xóa email sẽ làm tê liệt app Gmail, khiến runner không thể lấy OTP khôi phục nick TikTok.
     + Phải giữ nguyên tài khoản trên máy và gắn cờ cảnh báo `TIKTOK_LINKED_MAIL_NEEDS_REVIEW` để Operator quyết định thay mail TikTok trước khi gỡ.
   - Nếu email đó **KHÔNG LIÊN KẾT VỚI TIKTOK NÀO** (chỉ là mail ngâm thuần túy) VÀ **ĐÃ XÁC NHẬN DIE THẬT Ở TẦNG 2**:
     + Cho phép gỡ bỏ an toàn qua Android OS để giải phóng slot reg mới.
