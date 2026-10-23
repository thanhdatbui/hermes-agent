# Kiến Trúc Hybrid OCR vs XML & Các Cạm Bẫy Nhận Diện Farm (Follow Dominance & Stat Counters)

## 1. Khái quát kiến trúc Hybrid (Tại sao không thể thay thế toàn bộ XML bằng OCR?)

Khi tự động hóa ứng dụng di động phức tạp (như TikTok, Gmail, Outlook), quan điểm *"chỗ nào có dump XML thì vứt đi thay bằng OCR"* là một cái bẫy kiến trúc nghiêm trọng. Hệ thống farm chuyên nghiệp bắt buộc phải vận hành theo mô hình **HYBRID (Lai ghép thông minh theo phân lớp tác vụ)**:

| Tác vụ | Công nghệ tối ưu | Cơ chế phối hợp | Lý do kỹ thuật |
| :--- | :--- | :--- | :--- |
| **Dập Popup bất ngờ** (`benign_popup`) | **Fast OCR First-Line (0.3s)** $\to$ XML Fallback | Quét nhanh 5-10 từ khóa nút đóng (`"để sau"`, `"không phải bây giờ"`, `"hủy"`, `"đóng"`). Thấy là tap dập luôn trong 0.3s. | 90% popup là dạng lành tính. Dump XML tốn 5s - 15s làm nghẽn cổ chai và đứt nhịp nuôi lướt feed. |
| **Bấm nút hành động hay đổi ID** (`Follow`, `Tiếp tục`, `Lưu`, `Đăng nhập`) | **XML First-Line** $\to$ **OCR Fallback** | Đọc XML trước. Nếu TikTok cập nhật obfuscated ID mới (`id/fds` $\to$ `id/fmp` $\to$ `id/fo4`) khiến XML ra `unknown` $\to$ OCR cứu nguy bằng mắt nhìn. | XML cực nhanh nếu ID có sẵn trong cache/whitelist; OCR giải cứu tức thì khi TikTok đổi ID, chống timeout crash. |
| **Định danh tài khoản (@username / UID)** | **100% XML** (CẤM DÙNG OCR) | Chỉ dùng node XML trích xuất chuỗi text từ RAM Android. | OCR dễ nhầm lẫn các ký tự tương đồng: `0` vs `O`, `1` vs `l` vs `I`, dấu gạch dưới `_`. Nhầm 1 ký tự sẽ follow sai người lạ hoặc ghi đè hỏng Excel. |
| **Đọc trạng thái thuộc tính UI** | **100% XML** (CẤM DÙNG OCR) | Đọc `selected="true"`, `checked="true"`, `focused="true"`. | OCR chỉ là ảnh phẳng, hoàn toàn không thể biết tab nào đang được chọn hay checkbox 2FA đã được bật hay chưa. |
| **Ô nhập liệu rỗng (EditText)** | **100% XML** (CẤM DÙNG OCR) | Đọc node `android.widget.EditText` có `password="true"`. | Ô mật khẩu khi chưa nhập là khoảng trắng tinh, OCR không thấy chữ gì để định vị. |

---

## 2. Luật Ưu Tiên Follow Dominance (Chống bẫy nút "Nhắn tin")

### Hiện tượng thực tế trên Profile TikTok:
Nick **CHƯA follow** (hoặc vừa bấm follow nhưng bị TikTok server drop/nhả về trạng thái cũ) hoàn toàn **vẫn có thể hiển thị nút "Nhắn tin"**:
1. Tài khoản bật chế độ mở DM công khai.
2. Tài khoản đã follow mình trước (TikTok hiển thị cặp nút: `[Follow lại]` đỏ + `[Nhắn tin]` xám).
3. Tài khoản Business/Creator.

### Quy tắc phân loại bắt buộc (Follow Dominance Invariant):
- Nếu code chỉ thấy chữ `"Nhắn tin"` mà kết luận là `followed` $\to$ **False-Positive 100%**, báo khống follow thành công trong khi nick chưa hề được follow.
- **Quy tắc vàng:**
  * **CHƯA FOLLOW (`not_followed`):** Bất kể có nút "Nhắn tin" hay không, **chỉ cần CÒN nút `[Follow]`, `[Follow lại]`, `[Theo dõi]`** trong dải action ($y < 1200$, số từ $\le 3$) $\to$ **ƯU TIÊN TUYỆT ĐỐI KẾT LUẬN `not_followed`**.
  * **ĐÃ FOLLOW (`followed`):** Nút đỏ `Follow/Follow lại` bắt buộc phải biến mất hoàn toàn, chỉ còn lại:
    - `[Bạn bè]` (Mutual) + `[Nhắn tin]`
    - `[Đang theo dõi]` + `[Nhắn tin]`
    - Hoặc duy nhất 1 nút lớn `[Nhắn tin]` (CHỈ KHI `allow_message_alone=True`). Khi `allow_message_alone=False` (mặc định), màn hình chỉ có duy nhất nút `[Nhắn tin]` bắt buộc trả về `unknown` để fail-closed chống false-positive đối với tài khoản mở DM công khai nhưng chưa follow.
  * **LOẠI TRỪ TOP BAR FEED ($y_1 < 200$):** Các tabs trên đỉnh màn hình Feed (như `"Bạn bè"`, `"LIVE"`, `"Dành cho bạn"`) có $y_1 < 200$. Mặc định tham số `y_min = 200` để tránh việc OCR đọc trúng tab "Bạn bè" trên thanh điều hướng đỉnh rồi kết luận sai là đã follow.
  * **LỰA CHỌN TÂM NÚT THEO TRỌNG TÂM DỌC (`anchor_y`):** Khi có nhiều nút thỏa mãn điều kiện follow, `find_follow_button_center_ocr` ưu tiên ứng viên gần `anchor_y` nhất (mặc định trung tâm dải Y: `(y_min + y_max) // 2`), đồng thời ưu tiên nhãn chuẩn (`"follow"` priority 0 so với `"follow lai"` priority 1).
  * **CẦU DAO POPUP NHẠY CẢM DÙNG REGEX WORD BOUNDARY:** Quét từ khóa nhạy cảm (`mật khẩu`, `captcha`, `otp`, `đăng nhập`, `thanh toán`) phải dùng regex `\b` word boundary (`re.search(r"\b" + re.escape(sk) + r"\b", n_txt)`), tránh false-positive khi gặp từ ngữ vô hại có chứa chuỗi con (như "Prepayment" hay "Footprint").

---

## 2.1 Cạm bẫy thanh Tab điều hướng Top-Bar (Top-Nav Collision Trap)

Trên màn hình Video Feed hoặc màn hình chính của TikTok/Instagram, đỉnh màn hình ($y_1 < 200$) luôn có thanh chuyển tab điều hướng (`LIVE`, `Bạn bè`, `Đang follow`, `Dành cho bạn`).
- Nếu hàm phân loại OCR quét từ $y_{min} = 0$, text box `('Ban bé', (333, 141, 461, 175))` sẽ bị bắt và phán nhầm màn hình Feed đang xem video thành `followed`!
- **Quy tắc bất biến:** BẮT BUỘC đặt mặc định `y_min = 200` khi trích xuất hoặc phân loại nút hành động profile, triệt tiêu hoàn toàn nhiễu từ thanh tab trên cùng.

---

## 3. Cạm bẫy Substring Stat Counter (Nhãn Thống Kê Số Liệu)

### Phân biệt bản chất Text giữa Stat Counter vs Nút Action:
Dưới avatar trên Profile có 3 cột số liệu:
- Cột 1: `Đang follow` (hoặc `Đã follow` trên bản tiếng Việt)
- Cột 2: `Follower` (hoặc `Người theo dõi`)
- Cột 3: `Thích`

### 3 Bẫy Substring chết người:
1. **`"follow" in "follower"` = True:** Nút stat cột 2 chứa chữ "follow", kiểm tra substring đơn giản sẽ nhận nhầm cột follower thành nút bấm Follow!
2. **`"follow" in "127 Đã follow"` = True:** Cột 1 chứa số người đối phương đang follow, nhận nhầm thành nút Follow!
3. **`"da follow"` / `"dang follow"`:** Trong TikTok tiếng Việt, nhãn text của cột thống kê chính là `<node text="Đã follow" />` hoặc `"Đang follow"`. Nút bấm action thật sự của TikTok khi đã follow **KHÔNG BAO GIỜ** ghi "Đã follow" mà chỉ ghi `"Đang theo dõi"`, `"Bạn bè"`, `"Nhắn tin"`.

### Giải pháp kỹ thuật chuẩn hóa:
```python
STAT_COUNTER_PATTERNS = (
    r"follower", r"followers", r"dang\s+follow", r"da\s+follow"
)
STAT_COUNTER_REGEX = re.compile("|".join(STAT_COUNTER_PATTERNS), re.IGNORECASE)

def is_stat_counter(n_txt: str) -> bool:
    return bool(STAT_COUNTER_REGEX.search(n_txt))

def match_not_followed(n_txt: str) -> bool:
    if is_stat_counter(n_txt):
        return False
    if "dang theo doi" in n_txt:  # "Đang theo dõi" là nút đã follow
        return False
    if len(n_txt.split()) > 3:   # Bỏ qua Bio dài
        return False
    for kw in ("follow lai", "follow", "theo doi"):
        if re.search(r"\b" + re.escape(kw) + r"\b", n_txt):
            return True
    return False
```

---

## 4. Module Canonical trong `automation-core`

Toàn bộ logic đã được đóng gói chuẩn hóa tại:
- **Module:** `D:/Taadaa/automation-core/src/automation_core/ocr.py`
- **Unit Tests:** `D:/Taadaa/automation-core/tests/test_ocr.py` (100% offline, bao phủ telemetry, nonzero returncode, popup safety guard, follow dominance).

---

## 5. Quy Chuẩn Adapter Telemetry, Header Validation & Tempfile Cleanup (17/10/2026)

Khi tích hợp WinRT OCR vào Adapter/Engine (`FollowAdapter.ocr_screen`, `verify_after_tap`):
1. **Xác thực PNG Magic Bytes (`b"\x89PNG\r\n\x1a\n"`)**:
   - Không chỉ kiểm tra `len(png) < 100`. Nếu ADB bị lỗi hoặc trả về text banner cảnh báo, dữ liệu rác vẫn có thể vượt qua kiểm tra độ dài. Bắt buộc kiểm tra `png.startswith(b"\x89PNG\r\n\x1a\n")` để đảm bảo dữ liệu hợp lệ trước khi ghi file tạm.
2. **Deterministic Tempfile Cleanup trong khối `finally`**:
   - Việc gọi `unlink()` chỉ trong khối `try` sẽ làm rò rỉ file tạm trên đĩa khi OCR gặp `TimeoutError` hoặc crash bất ngờ.
   - Luôn dọn dẹp file tạm trong khối `finally` kèm try-catch `OSError` để ghi log cảnh báo (`ocr_temp_cleanup_failed`) thay vì làm crash luồng chính.
3. **Structured Telemetry thay cho Silent Swallowing**:
   - CẤM nuốt ngoại lệ im lặng (`except Exception: return []` hoặc `pass`). Bắt buộc ghi log có cấu trúc: thời gian `elapsed`, `serial`, nguyên nhân thất bại (`invalid_screencap`, `timeout`, `ocr_error`), và loại ngoại lệ `error_type=type(exc).__name__` để hỗ trợ giám sát vận hành dài hạn.
