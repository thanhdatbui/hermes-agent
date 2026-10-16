# Kiến trúc Hybrid: Phối hợp WinRT OCR Native và UI XML trên Farm Android

## 1. Bản chất sự khác biệt kỹ thuật

| Đặc tính | Dump UI XML (`uiautomator dump` / `atx-agent`) | WinRT OCR Native (`ocr_boxes.ps1`) |
| :--- | :--- | :--- |
| **Bản chất dữ liệu** | Điện thoại Android xuất toàn bộ cây cấu trúc phân cấp ra file XML text (`<node resource-id="..." text="..." />`). | Chụp ảnh màn hình (`screencap`), dùng engine thị giác máy tính của Windows (WinRT) đọc thẳng chữ trên ảnh. |
| **Tốc độ xử lý** | **Chậm (3s – 15s/lần)**. Khi máy lag hoặc màn hình đang cuộn có thể mất tới 30s – 45s, gây nghẽn cổ chai. | **Cực nhanh (0.3s – 0.5s/lần)**. Chụp ảnh 0.2s + OCR 0.1s trên CPU Windows. Nhanh gấp 10 – 20 lần XML. |
| **Khi TikTok đổi ID nút** | **GÃY NGAY LẬP TỨC**. TikTok bản 46.x/47.x liên tục đổi obfuscated ID: `id/fds` $\to$ `id/ff8` $\to$ `id/fm9` $\to$ `id/fmp` $\to$ `id/fo4`... Mỗi lần đổi là script bị mù, phải soi XML để vá selector. | **MIỄN NHIỄM 100%**. Bất kể ID mã hóa thành cái gì, mắt người nhìn thấy chữ "Follow", "Theo dõi", "Follow lại" thì OCR đọc được đúng chữ đó. |
| **Vị trí bấm (Target)** | Dễ dính lỗi *flatten hierarchy*: Chữ "Follow" nằm ở textview `clickable=false`, còn nút bấm thật là container bọc ngoài không có text $\to$ dễ tap trượt. | Nhìn thẳng vào chữ, lấy luôn tọa độ tâm hộp chữ $(cx, cy)$ trên ảnh để tap chính xác 100%. |
| **Ngữ cảnh cấu trúc** | Hiểu được cây cha - con, biết node nào là nút bấm, node nào là nhãn thống kê hay mô tả. | **Nhìn phẳng (Flat vision)**: Chỉ thấy chữ và tọa độ hộp chữ, không biết chữ nào là nút, chữ nào là Bio hay số đếm nếu không có luật lọc. |

---

## 2. Phân định ranh giới kiến trúc (Task-Based Tiering)

Tuyệt đối KHÔNG thay thế toàn bộ XML bằng OCR một cách mù quáng. Hệ thống áp dụng mô hình phân tầng theo tính chất tác vụ:

### Tier 1: Dập Popup đè màn hình $\to$ **OCR FIRST-LINE (0.3s) $\to$ Fallback XML**
- **Tại sao:** 90% popup trên TikTok là các dạng lành tính: *"Để sau"*, *"Không phải bây giờ"*, *"Hủy"*, *"Đóng"*, *"Bỏ qua"*, *"Not now"*, *"Later"*.
- **Cơ chế:**
  1. Quét OCR siêu tốc (0.2s - 0.3s). Thấy đúng các chữ nút đóng này $\to$ Tap dập tắt ngay lập tức. Không cần tốn 5s - 15s dump XML chỉ để tìm 1 nút "Để sau".
  2. **Cầu dao an toàn (Safety Guard):** Nếu trên màn hình xuất hiện bất kỳ từ khóa nhạy cảm nào (`mật khẩu`, `captcha`, `otp`, `đăng nhập`, `thanh toán`, `credential`), hàm lập tức trả về `None`, **tuyệt đối không bao giờ click bừa vào màn hình thử thách hay bảo mật**.
  3. Chỉ khi OCR không nhận ra hoặc màn hình vẫn bị kẹt sau tap $\to$ mới gọi XML chuyên sâu của `benign_popup.py` để phân tích state machine đầy đủ.

### Tier 2: Bấm nút thay đổi ID (`Follow`, `Tiếp tục`, `Đăng ký`) $\to$ **XML TRƯỚC $\to$ OCR FALLBACK**
- **Tại sao:** XML đọc cây node trực tiếp từ RAM máy, nếu ID nằm trong whitelist thì chỉ mất 0.1s.
- **Cơ chế:**
  1. Đọc XML trước.
  2. Nếu XML trả về `unknown` (TikTok vừa cập nhật đổi sang ID mới như `id/fmp`, `id/fo4`) $\to$ Kích hoạt ngay OCR Fallback để cứu nguy, nhìn thẳng vào chữ "Follow" để bấm luôn, **không để bị timeout hay crash script**.

### Tier 3: Định danh tài khoản, Mật khẩu, Checkbox, Token $\to$ **100% XML (CẤM DÙNG OCR)**
- **Đọc `@username` để đối soát Excel:** OCR rất dễ nhầm `0` với `O`, `l` với `1`. Sai 1 ký tự sẽ dẫn tới follow nhầm hoặc ghi đè nhầm nick farm.
- **Thuộc tính trạng thái:** `selected="true"` (tab nào đang chọn), `checked="true"` (checkbox điều khoản / bật 2FA), `focused="true"` (con trỏ đang ở ô nào). OCR là ảnh phẳng, hoàn toàn không biết các thuộc tính này.
- **Ô nhập liệu trống (Empty Input / EditText):** Ô password khi chưa gõ là khoảng trắng, OCR không thấy gì. Chỉ XML mới xác định được node EditText `password="true"`.

---

## 3. Các cạm bẫy sống còn khi lập trình OCR trên TikTok

### Cạm bẫy 1: Bẫy cặp nút song song `[Follow]` + `[Nhắn tin]` (Follow Dominance Invariant)
- **Hiện tượng:** Nick **CHƯA FOLLOW** hoàn toàn có thể hiển thị cả 2 nút song song:
  - Nút đỏ: `[Follow]` (hoặc `[Follow lại]`)
  - Nút xám: `[Nhắn tin]` (khi nick mở DM công khai hoặc họ đã follow mình trước).
- **Hậu quả nếu code ẩu:** Kiểm tra `if "nhan tin" in text:` rồi kết luận `followed` $\to$ Báo thành công khống 100% khi chưa follow hoặc khi bị TikTok âm thầm nhả follow (drop follow).
- **Quy tắc bất biến (Follow Dominance):** Cứ nhìn thấy từ khóa chưa follow (`"follow"`, `"follow lại"`, `"theo dõi"`) $\to$ **Ưu tiên tuyệt đối kết luận `not_followed`**, bất kể có chữ "nhắn tin" bên cạnh hay không. Chỉ khi nút đỏ Follow biến mất hoàn toàn và xuất hiện nút quan hệ (`[Bạn bè]`, `[Đang follow]`) hoặc chỉ còn duy nhất 1 nút `[Nhắn tin]` mới được kết luận `followed`.

### Cạm bẫy 2: Bẫy nhãn thống kê (Stat Counters)
- Dưới avatar luôn có 3 cột: `Follower` | `Đang follow` (hoặc `Đã follow`) | `Thích`.
- `"follower"` chứa `"follow"`, `"127 Đã follow"` chứa `"follow"`. Kiểm tra substring thông thường sẽ nhận nhầm cột số đếm thành nút Follow!
- `"dang theo doi"` chứa `"theo doi"`. `"dang theo doi"` là nhãn đã follow (`followed`), nhưng `"theo doi"` lại là nút chưa follow (`not_followed`). Bắt buộc loại trừ `"dang theo doi"` trước khi kiểm tra `"theo doi"`.
- **Giải pháp:** Sử dụng regex lọc stat counter và word boundaries `\b`:
  ```python
  STAT_COUNTER_PATTERNS = (r"follower", r"followers", r"dang\s+follow", r"da\s+follow")
  ```

### Cạm bẫy 3: Bẫy text phần Bio (Mô tả trang cá nhân)
- Rất nhiều người dùng ghi Bio dạng: *"Nhắn tin Zalo..."*, *"Follow ủng hộ mình nhé..."*.
- Quét OCR toàn màn hình không giới hạn tọa độ sẽ đọc trúng text Bio.
- **Giải pháp:** Bắt buộc khoanh vùng dải header action ($y < 1200$), loại bỏ hoàn toàn các box nằm ngoài dải này.

---

## 4. Chuẩn mực API dùng chung trong `automation_core.ocr`

Tất cả các repo consumer (`tiktok-follow`, `tiktok-luot nuoi acc`, `Tiktok_Reg`) gọi chung qua:

```python
from automation_core.ocr import (
    ocr_screen_boxes,
    find_popup_dismiss_button_ocr,
    classify_profile_action_ocr,
    find_follow_button_center_ocr,
)
```

1. **`find_popup_dismiss_button_ocr(boxes)`**: Dập popup lành tính trong 0.3s, tự ngắt khi có captcha/login.
2. **`classify_profile_action_ocr(boxes)`**: Phân loại quan hệ profile tuân thủ Follow Dominance.
3. **`find_follow_button_center_ocr(boxes)`**: Tìm tọa độ $(cx, cy)$ nút Follow đỏ để tap chính xác.
