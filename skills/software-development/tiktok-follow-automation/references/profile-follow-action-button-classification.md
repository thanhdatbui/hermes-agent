# Quy tắc phân loại nút Follow & Nhắn tin trên Profile TikTok (Follow Dominance & OCR Invariants)

## 1. Hiện tượng thực tế trên UI TikTok
Rất nhiều tài khoản **CHƯA FOLLOW** (hoặc vừa tap nhưng bị server TikTok drop/nhả follow về trạng thái ban đầu) hoàn toàn **vẫn hiển thị nút/chữ "Nhắn tin" (Message)** trên header Profile:
- **Tài khoản mở DM công khai:** Hiển thị cặp 2 nút song song: Nút đỏ `[Follow]` (hoặc `[Theo dõi]`) bên trái và Nút xám `[Nhắn tin]` bên phải.
- **Tài khoản đã follow mình trước:** Hiển thị cặp 2 nút song song: Nút đỏ `[Follow lại]` bên trái và Nút xám `[Nhắn tin]` bên phải.
- **Tài khoản Doanh nghiệp / Creator:** Nút nhắn tin / email / liên hệ luôn hiển thị công khai bất kể trạng thái follow.

## 2. Cạm bẫy False-Positive (Sai lầm chết người)
- Nếu parser chỉ kiểm tra sự xuất hiện của chữ `"Nhắn tin"` / `"Message"` mà kết luận ngay là tài khoản đã `followed`, hệ thống sẽ bị lừa 100% trên các tài khoản mở DM hoặc follow mình trước.
- Khi bot bấm Follow nhưng bị TikTok âm thầm nhả lại (drop follow), màn hình reload sẽ hiện lại cặp `[Follow lại]` + `[Nhắn tin]`. Nếu parser nhận diện nhầm "Nhắn tin" là followed thì bot sẽ báo thành công khống, trong khi thực tế nick đang bị drop follow (dẫn đến không kích hoạt kịp thời cơ chế dừng session bảo vệ tài khoản).

## 3. Nguyên tắc phân loại chuẩn xác (Follow Dominance Invariant)

### A. Trạng thái CHƯA FOLLOW (`not_followed`):
- **Ưu tiên tuyệt đối (Follow Dominance):** Chỉ cần **CÒN TỒN TẠI** nút `[Follow]`, `[Follow lại]`, hoặc `[Theo dõi]`.
- Dù bên cạnh có nút `[Nhắn tin]` hay không, sự xuất hiện của nút Follow/Follow lại luôn có độ ưu tiên cao nhất, khẳng định trạng thái quan hệ hiện tại là **CHƯA FOLLOW**.

### B. Trạng thái ĐÃ FOLLOW (`followed`):
- **Điều kiện cốt lõi:** Nút `[Follow]` / `[Follow lại]` **bắt buộc phải biến mất hoàn toàn**.
- Thay vào đó, nút action chuyển thành:
  - `[Bạn bè]` (Mutual) + `[Nhắn tin]`
  - `[Đang follow]` / `[Đang theo dõi]` + `[Nhắn tin]`
  - Hoặc TikTok thu gọn thành duy nhất 1 nút lớn `[Nhắn tin]` (không còn bất kỳ nút Follow nào trên header).

### C. Trạng thái KHÔNG XÁC ĐỊNH (`unknown`):
- Không khớp các tiêu chí trên hoặc màn hình lỗi layout/chưa tải xong $\rightarrow$ Fail-closed, reload kiểm tra lại hoặc chuyển trạng thái an toàn.

## 4. Kỷ luật cài đặt mã nguồn (XML & WinRT OCR)

### A. Trong bộ phân tích XML (`verify_follow.py`):
- Whitelist đầy đủ các resource ID nút action theo từng phiên bản TikTok (`id/fds`, `id/ff8`, `id/fm9`, `id/fmp`, `id/fo4`...).
- Khi có đúng 1 nút `not_followed` (`Follow`/`Follow lại`) và 1 nút `Nhắn tin`, bắt buộc phân loại là `not_followed`.

### B. Trong bộ phân tích OCR (`ocr.py` & `automation_core.ocr`):
1. **Khử bẫy Substring:**
   - `"follower"` chứa `"follow"`, `"127 Đã follow"` / `"0 Đang follow"` chứa `"follow"`. Nếu dùng kiểm tra substring `kw in text` sẽ nhận nhầm cột thống kê thành nút Follow!
   - `"dang theo doi"` chứa `"theo doi"`. `"dang theo doi"` là nhãn đã follow (`followed`), nhưng `"theo doi"` lại là nút chưa follow (`not_followed`). Bắt buộc loại trừ `"dang theo doi"` trước khi kiểm tra `"theo doi"`.
2. **Loại trừ nhãn đếm (Stat Counters):**
   - Bắt buộc lọc qua regex `r"follower"`, `r"followers"`, `r"dang\s+follow"`, `r"da\s+follow"` và word boundaries `\b`.
3. **Giới hạn dải Action Band ($y < 1200$):**
   - Nút bấm hành động chỉ nằm ở khoảng $y$ từ 450 đến 850 (trên màn hình chuẩn).
   - Giới hạn $y < 1200$ để loại bỏ hoàn toàn phần text mô tả (Bio) bên dưới (tránh dính text Bio như *"Nhắn tin Zalo..."*, *"Follow ủng hộ mình nhé..."*).

## 5. Kiến Trúc Phối Hợp Hybrid (XML vs WinRT OCR)
Tuyệt đối không thay thế toàn bộ XML bằng OCR một cách mù quáng:

| Tác vụ | Mô hình tối ưu | Lý do kỹ thuật |
| :--- | :--- | :--- |
| **Dập Popup đè màn hình (`benign_popup`)** | **OCR First-Line (0.3s)** $\rightarrow$ Fallback XML | 90% popup là từ khóa quen thuộc (`"để sau"`, `"không phải bây giờ"`, `"hủy"`, `"đóng"`). OCR quét dập ngay trong 0.3s, không làm đứt nhịp nuôi video. |
| **Bấm nút đổi ID (`Follow`, `Tiếp tục`)** | **XML trước $\rightarrow$ OCR Fallback** | Đọc XML theo selector. Nếu TikTok đổi obfuscated ID (`id/fds` $\to$ `id/fmp` $\to$ `id/fo4`) khiến XML ra `unknown` $\rightarrow$ OCR nhìn chữ để tap cứu nguy, chống timeout. |
| **Định danh UID (@handle), Checkbox, Focus** | **100% XML (CẤM DÙNG OCR)** | OCR là ảnh phẳng, không đọc được `selected="true"`, `checked="true"`, ô pass rỗng và dễ nhầm ký tự UID (`0`/`O`, `1`/`l`). |

## 6. Cạm bẫy Optimistic UI Cache trong Path B Verify
- **Nguyên nhân lệch số liệu giữa Runner và Web:** Khi tài khoản bị shadowban hoặc bị TikTok ngắt quyền follow ngầm (silent-drop), cú tap Follow trong danh sách khiến client app TikTok lưu tạm trạng thái optimistic.
- **Sai lầm chết người:** Mở profile nick vừa follow mà **KHÔNG vuốt kéo reload (`pull_to_refresh_profile`)** vì lầm tưởng việc chuyển màn hình đã tải lại dữ liệu mới. Thực tế app TikTok vẫn hiển thị cache cục bộ (nút "Nhắn tin"), khiến runner ghi nhận thành công trong khi server TikTok thực tế là `0` lượt follow.
- **Quy tắc bắt buộc:** 100% các bước verify sau tap (cả Anchor lẫn Path B verify từng nick) **BẮT BUỘC thực hiện pull-to-refresh có jitter** để ép app TikTok kéo dữ liệu thực từ server về trước khi phân loại (XML hoặc OCR).
