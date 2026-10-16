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
- **Đối xứng Semantic Matcher trong `_is_profile_action_node`:**
  - Bắt buộc nhận diện các nút `not_followed` (`Follow`, `Follow lại`, `Theo dõi`) bằng semantic text/content-desc (`bounds[1] < 1200`) giống như `message_markers`, KHÔNG ĐƯỢC chỉ phụ thuộc cứng vào danh sách ID cũ `_ACTION_BUTTON_SUFFIXES`.
  - Nếu chỉ nhận diện `Nhắn tin` theo text còn `Follow` theo resource ID, khi TikTok đổi ID nút Follow (như `id/fo4`, `id/fmp`), nút Follow bị lọt lưới $\rightarrow$ XML chỉ còn nút Nhắn tin $\rightarrow$ phán nhầm `followed`!
- Khi có đúng 1 nút `not_followed` (`Follow`/`Follow lại`) và 1 nút `Nhắn tin`, bắt buộc phân loại là `not_followed`.
- Trong các hàm fallback (như `_classify_profile_action` trong Mode 2), danh sách `followed_kw` TUYỆT ĐỐI CẤM chứa `"nhắn tin"`, `"message"`, `"send message"` — chỉ chấp nhận `"đang theo dõi"`, `"following"`, `"friends"`, `"bạn bè"`.

### B. Trong bộ phân tích OCR (`ocr.py` & `automation_core.ocr`):
1. **Khử bẫy "Nhắn tin" trong `FOLLOWED_KEYWORDS`:**
   - CẤM TUYỆT ĐỐI đưa `"nhan tin"`, `"message"`, `"gui tin nhan"` vào danh sách `FOLLOWED_KEYWORDS` của OCR.
   - Khi OCR chỉ thấy duy nhất nút `Nhắn tin` (do camera/OCR bỏ sót nút `Follow` màu đỏ vì tương phản nền), OCR BẮT BUỘC trả về `unknown` (fail-closed), TUYỆT ĐỐI CẤM phán `followed`.
   - `FOLLOWED_KEYWORDS` trong OCR CHỈ chấp nhận: `"dang theo doi"`, `"ban be"`, `"friends"`, `"following"`.
2. **Khử bẫy Substring:**
   - `"follower"` chứa `"follow"`, `"127 Đã follow"` / `"0 Đang follow"` chứa `"follow"`. Nếu dùng kiểm tra substring `kw in text` sẽ nhận nhầm cột thống kê thành nút Follow!
   - `"dang theo doi"` chứa `"theo doi"`. `"dang theo doi"` là nhãn đã follow (`followed`), nhưng `"theo doi"` lại là nút chưa follow (`not_followed`). Bắt buộc loại trừ `"dang theo doi"` trước khi kiểm tra `"theo doi"`.
3. **Loại trừ nhãn đếm (Stat Counters) & Khóa độ dài chữ (Word Length Guard):**
   - Bắt buộc lọc qua regex `r"follower"`, `r"followers"`, `r"dang\s+follow"`, `r"da\s+follow"` và word boundaries `\b`.
   - **Khóa độ dài nhãn nút bấm:** Nút hành động chuẩn trên TikTok chỉ có từ 1 đến 3 từ (`"Follow"`, `"Follow lại"`, `"Theo dõi"`). Bắt buộc kiểm tra `len(n_txt.split()) <= 3`; nếu vượt quá 3 từ (dù có chứa từ "follow") thì lập tức loại bỏ, tránh tuyệt đối việc câu mô tả trong Bio bị nhận nhầm thành nút bấm.
4. **Giới hạn dải Action Band ($y < 1200$):**
   - Nút bấm hành động chỉ nằm ở khoảng $y$ từ 450 đến 850 (trên màn hình chuẩn).
   - Giới hạn $y < 1200$ để loại bỏ hoàn toàn phần text mô tả (Bio) bên dưới (tránh dính text Bio như *"Nhắn tin Zalo..."*, *"Follow ủng hộ mình nhé..."*).
5. **Cầu dao an toàn khi dập Popup (Popup Safety Guard):**
   - Tuyệt đối không bấm nút đóng popup nếu trên màn hình xuất hiện bất kỳ từ khóa nhạy cảm / bảo mật nào: `mật khẩu`, `captcha`, `otp`, `đăng nhập`, `thanh toán`, `credential`, `payment`.
6. **Telemetry & Audit Logging:**
   - Mọi hàm phân loại (`classify_profile_action_ocr`, `find_follow_button_center_ocr`, `find_popup_dismiss_button_ocr`) bắt buộc ghi log rõ ràng `decision=...` và `reason=...` để phục vụ Closeout Review và audit truy vết hành vi farm.
7. **Modular Hóa Dùng Chung (`automation_core.ocr`):**
   - Toàn bộ tiện ích WinRT OCR native, fast popup dismissal và profile action classification đã được đóng gói chuẩn tại `from automation_core.ocr import ocr_screen_boxes, find_popup_dismiss_button_ocr, classify_profile_action_ocr, find_follow_button_center_ocr`. Các consumer repo tái sử dụng trực tiếp từ đây, cấm viết lại module rời rạc.

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

## 7. Bẫy Bất Đối Xứng trong `_is_profile_action_node` & Kỷ luật Canary khi Farm đang chạy ca

### A. Bẫy Bất Đối Xứng (Asymmetric Action Node Matcher):
- **Hiện tượng:** Trong `_is_profile_action_node`, nút Nhắn tin được nhận diện tự do qua semantic text (`values & message_markers`) cho mọi ID, trong khi nút Follow lại bị ép cứng theo whitelist ID (`_ACTION_BUTTON_SUFFIXES`).
- **Hậu quả:** Khi TikTok cập nhật obfuscated ID mới cho nút Follow (như `id/fmp`, `id/fo4`), nút Follow bị loại khỏi `action_nodes`, chỉ còn nút Nhắn tin lọt qua $\rightarrow$ `classify_button` tưởng màn hình không còn nút Follow và trả về `followed` khống!
- **Kỷ luật sửa:** Nhận diện nút hành động bắt buộc đối xứng: mở rộng `action_text_markers` bao gồm cả `FOLLOW_BUTTON_TEXT + FOLLOW_BACK_TEXT + FOLLOWED_TEXT` cho vùng `bounds[1] < 1200` (loại trừ stat counters).

### B. Kỷ luật Canary khi Farm đang chạy ca (Active Cohort Isolation):
- Khi User yêu cầu: *"Làm xong chạy canary vài acc kiểm tra xem lỗi không"*:
  1. **Preflight kiểm tra lịch Farm (`psutil` / manifests):** Kiểm tra xem có ca nuôi nào đang chạy live hay không (ví dụ Ca 3 Row 6 `multi-machine-feed-session`).
  2. **CẤM TUYỆT ĐỐI chạy canary đè lệnh ADB** lên máy đang trong phiên nuôi active (tránh race condition, xung đột socket và vỡ phiên).
  3. **Tận dụng khe rảnh giữa các phiên (Pair Gap):** Chờ phiên hiện tại kết thúc (khoảng nghỉ giữa P1 và P2 thường là 45-60 phút) hoặc bốc các máy đã chạy xong P1 sớm và đã nhả sạch lock thiết bị.
  4. **Quy trình Canary chuẩn:** Acquire device lock (`user_authorized=True`) -> Chạy canary -> Soi mắt kiểm tra ảnh thực tế (`MEDIA:`) -> Nhả lock và báo cáo.

## 8. Ma Trận Canary Đa Dạng Màn Hình (Multi-Scenario Canary Matrix)
*User directive:* *"Canary nên chạy nhiều trường hợp để nắm đc script có ổn định khi gặp nhiều màn khác nhau k ấy"*. Tuyệt đối không chỉ canary 1 máy hoặc 1 layout đơn điệu rồi kết luận thành công. Khi nghiệm thu bản vá phân loại quan hệ / follow, bắt buộc kiểm thử tối thiểu qua 5 kịch bản thực tế:

1. **Kịch bản 1 — Nick Creator / Công khai (Mở DM):**
   - *Giao diện:* Cặp nút song song `[Follow]` (Đỏ) + `[Nhắn tin]` (Xám).
   - *Kỳ vọng:* Nhận diện chuẩn xác `not_followed`, tap trúng nút Follow đỏ. CẤM phán nhầm `followed`.
2. **Kịch bản 2 — Nick Riêng Tư / Khóa DM:**
   - *Giao diện:* Chỉ có duy nhất 1 nút lớn `[Follow]` (Đỏ) với các obfuscated ID khác nhau (`id/fds`, `id/fo4`, `id/fmp`).
   - *Kỳ vọng:* Nhận diện chuẩn `not_followed` qua semantic text khi ID thay đổi.
3. **Kịch bản 3 — Nick Đã Follow Thành Công:**
   - *Giao diện:* Sau khi tap & pull-to-refresh: nút đổi thành `[Đang theo dõi]` hoặc `[Bạn bè]`.
   - *Kỳ vọng:* Nhận diện đúng `followed`, phân biệt rạch ròi với stat counter (số `120 Đang follow`).
4. **Kịch bản 4 — Bẫy Nhả Follow (Ghost / Shadow Reject):**
   - *Giao diện:* Vừa tap xong app hiện `Đang theo dõi`, nhưng sau khi vuốt kéo reload (`pull_to_refresh_profile`) thì app giật ngược về nút `[Follow]` đỏ.
   - *Kỳ vọng:* Bắt sống `FOLLOW_FAILED`, kích hoạt cầu dao an toàn dừng ca, không ghi nhận điểm follow ảo vào database.
5. **Kịch bản 5 — Giao diện Danh sách Following (Mode 2 Rows):**
   - *Giao diện:* Danh sách follower cuộn dọc gồm nhiều hàng xen kẽ (Nút `Follow`, `Follow lại`, `Bạn bè`).
   - *Kỳ vọng:* Nhận diện đúng từng row nội bộ, skip các row đã follow, tap chuẩn xác không lệch tọa độ khi cuộn.
- **Tiêu chuẩn chọn máy Canary:** Chọn tối thiểu 2-3 máy đại diện các thế hệ ID/layout khác nhau trên farm (ví dụ Máy 1 layout `id/fds`, Máy 2 layout `id/ff8`, Máy 6 layout `id/fij`), kiểm tra trực tiếp qua `with_device_lock.py` và đính kèm ảnh `MEDIA:` soi mắt trước khi báo cáo.
