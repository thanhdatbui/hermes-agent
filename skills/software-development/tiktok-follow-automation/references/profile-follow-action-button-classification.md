# Quy tắc phân loại nút Follow & Nhắn tin trên Profile TikTok

## 1. Hiện tượng thực tế trên UI TikTok
Rất nhiều tài khoản **CHƯA FOLLOW** (hoặc bị server TikTok nhả follow) vẫn hiển thị nút/chữ **"Nhắn tin"** (Message) trên header Profile:
- **Tài khoản mở DM công khai:** Hiển thị cặp 2 nút song song: Nút đỏ `[Follow]` (hoặc `[Theo dõi]`) bên trái và Nút xám `[Nhắn tin]` bên phải.
- **Tài khoản đã follow mình trước:** Hiển thị cặp 2 nút song song: Nút đỏ `[Follow lại]` bên trái và Nút xám `[Nhắn tin]` bên phải.
- **Tài khoản Doanh nghiệp / Creator:** Nút nhắn tin / email / liên hệ luôn hiển thị công khai bất kể trạng thái follow.

## 2. Cạm bẫy False-Positive (Sai lầm chết người)
- Nếu parser chỉ kiểm tra sự xuất hiện của chữ `"Nhắn tin"` / `"Message"` mà kết luận ngay là tài khoản đã `followed`, hệ thống sẽ bị lừa 100% trên các tài khoản mở DM hoặc follow mình trước.
- Khi bot bấm Follow nhưng bị TikTok âm thầm nhả lại (drop follow), màn hình reload sẽ hiện lại cặp `[Follow lại]` + `[Nhắn tin]`. Nếu parser nhận diện nhầm "Nhắn tin" là followed thì bot sẽ báo thành công khống, trong khi thực tế nick đang bị drop follow (dẫn đến không kích hoạt kịp thời cơ chế dừng session bảo vệ tài khoản).

## 3. Nguyên tắc phân loại chuẩn xác (XML & OCR)

### A. Trạng thái CHƯA FOLLOW (`not_followed`):
- **Điều kiện cốt lõi:** Chỉ cần **CÒN TỒN TẠI** nút `[Follow]`, `[Follow lại]`, hoặc `[Theo dõi]`.
- Dù bên cạnh có nút `[Nhắn tin]` hay không, sự xuất hiện của nút Follow/Follow lại luôn có độ ưu tiên cao nhất, khẳng định trạng thái quan hệ hiện tại là **CHƯA FOLLOW**.

### B. Trạng thái ĐÃ FOLLOW (`followed`):
- **Điều kiện cốt lõi:** Nút `[Follow]` / `[Follow lại]` **bắt buộc phải biến mất hoàn toàn**.
- Thay vào đó, nút action chuyển thành:
  - `[Bạn bè]` (Mutual) + `[Nhắn tin]`
  - `[Đang follow]` / `[Đang theo dõi]` + `[Nhắn tin]`
  - Hoặc TikTok thu gọn thành duy nhất 1 nút lớn `[Nhắn tin]` (không còn bất kỳ nút Follow nào trên header).

## 4. Kỷ luật cài đặt mã nguồn
- **Trong bộ phân tích XML (`verify_follow.py`):**
  - Whitelist đầy đủ các resource ID nút action theo từng phiên bản TikTok (`id/fds`, `id/ff8`, `id/fm9`, `id/fmp`, `id/fo4`...).
  - Khi có đúng 1 nút `not_followed` (`Follow`/`Follow lại`) và 1 nút `Nhắn tin`, bắt buộc phân loại là `not_followed`.
- **Trong bộ phân tích OCR (`ocr.py`):**
  - Khi OCR phát hiện text chứa từ khóa `not_followed` (`follow lai`, `follow`, `theo doi`), bắt buộc ưu tiên kết luận `not_followed`, không để từ khóa `nhan tin` làm nhiễu khiến bộ phân loại rơi vào `unknown`.
