# ChatGPT Linking on Samsung S7 Android 8: Root Causes, Password Policy & Full Resolution (24/09/2026)

## Context & Symptoms
Trong ca sau trưa ngày 24/09/2026, watchdog báo cáo kết quả:
- **Reg Gmail**: 8/15 thành công.
- **ChatGPT Linked**: 0/8 (100% fail tại bước link ChatGPT qua `hook_chatgpt_register.py`).

Qua quá trình debug và bóc tách từng frame trên thiết bị thật (Máy 22, Máy 24, Máy 16, Máy 13), đã xác định được 4 nguyên nhân gốc rễ và cơ chế giải quyết triệt để.

---

## 4 Root Causes & Technical Pitfalls

### 1. OpenAI Password Policy Enforcement (>= 12 Ký Tự)
- **Hiện tượng**: Tại màn hình "Tạo mật khẩu", OpenAI bắt buộc `Ít nhất 12 ký tự`. Mật khẩu do `build_password()` sinh cho Gmail trước đây có độ dài 10-11 ký tự (floor `len < 10`). OpenAI báo đỏ `X Ít nhất 12 ký tự` và vô hiệu hóa nút Tiếp tục.
- **Giải pháp 2 tầng (Tránh thêm cột Excel/DB)**:
  - **Tầng 1 (Acc mới)**: Nâng floor trong `build_password()` của `gmail_reg_v10.py` lên `while len(p) < 13:` (tạo mật khẩu 13–20 ký tự). Cả Gmail và ChatGPT cùng dùng chung 1 pass gốc trong file Excel mà không làm lệch index cột.
  - **Tầng 2 (Acc cũ / Fallback)**: Nếu pass cũ có độ dài < 12 ký tự, tự động nối thêm suffix xác định `@2026` (`pw_to_type = f"{pw_to_type}@2026"`).

### 2. Gmail Auto-Sync Off, Thread Grouping & Bẫy `max_check_attempts`
- **Hiện tượng**: Tính năng Auto-sync trên Farm mặc định tắt. App Gmail tự động gom tất cả email xác nhận OpenAI gửi về thành 1 luồng hội thoại (`thread`). Nếu mở Gmail mà không kéo làm mới, thư mới chưa tải về ngay. Script cũ dùng regex phẳng quét toàn XML nên bốc nhầm mã OTP của thư cũ/thư hết hạn. Nhập sai 3 lần khiến OpenAI kích hoạt khóa chống brute-force:
  `error_code: max_check_attempts` (*Bạn đã thử quá nhiều lần. Vui lòng đợi vài phút rồi thử lại*).
- **Giải pháp**:
  - Vuốt kéo làm mới danh sách thư ở vùng an toàn: `shell(serial, "input", "swipe", "540", "800", "540", "1600", "400")` hoặc `(540, 1350) -> (540, 1800)`.
  - Phân tích XML theo cây DOM (`ElementTree`): Ưu tiên trích xuất OTP từ node thư đầu tiên trên đỉnh Inbox (`OpenAI`, `tiếp tục: \d{6}`), bỏ qua các node thư cũ nằm phía dưới.

### 3. Bàn Phím Ảo Samsung Đẩy Nút Tiếp Tục Lên (540, 762) & Bẫy Phím 'g'
- **Hiện tượng**: Sau khi gõ email vào WebView Chrome trên Android 8, bàn phím ảo đẩy form lên. Nút *Tiếp tục* nằm ở tọa độ `(540, 762)`.
  Nếu tap vào tọa độ tĩnh vùng dưới `(540, 1504)`, tap sẽ rơi trúng phím chữ **`g`** trên bàn phím ảo, khiến email bị biến dạng thành `@gmail.comg`.
- **Giải pháp**:
  - Gõ email xong -> Tap ngay tọa độ nổi `(540, 762)` kết hợp gửi Enter (`keyevent 66`).
  - CẤM dùng `keyevent 111` (Escape) trên Android 8 vì sẽ thu nhỏ Chrome về Launcher. Dùng `keyevent 4` (Back) nếu cần hạ bàn phím.

### 4. Kẹt Search Mode Trong App Gmail
- **Hiện tượng**: Khi mở app Gmail, nếu trạng thái trước đó đang ở ô tìm kiếm, bàn phím ảo sẽ che khuất Inbox. Thao tác tap nút Quay lại `(72, 168)` không ăn do bàn phím đang chiếm input focus.
- **Giải pháp**:
  - Kiểm tra điều kiện: `any(k in xml for k in ["Tệp đính kèm", "Xoá văn bản", "Tìm kiếm trong thư"]) and "Quay lại" in xml`.
  - Gửi 2 lần phím Back (`keyevent 4`) liên tiếp cách nhau 0.5s: lần 1 hạ bàn phím, lần 2 thoát chế độ tìm kiếm về danh sách Inbox chính.

---

## Canonical Step Coordinates (Samsung S7 SM-G930F 1080x1920)

| Bước | Thành phần | Tọa độ chuẩn (X, Y) | Ghi chú |
|---|---|---|---|
| **Step 1** | Cookie Banner: Chấp nhận tất cả | `(540, 1662)` | Dismiss popup che khuất màn hình |
| **Step 1** | Email Address Input Field | `(540, 1315)` hoặc `(400, 1314)` | Nhập email clean |
| **Step 1** | Nút Tiếp tục (khi bàn phím mở) | `(540, 762)` | Tránh tap phím 'g' tại (540, 1504) |
| **Step 2** | Swipe refresh Gmail Inbox | `(540, 800) -> (540, 1600)` | Kéo đồng bộ thư mới nhất |
| **Step 3** | OTP Input Field (Chrome) | `(540, 1146)` | Nhập 6 số OTP |
| **Step 3** | Submit OTP | `keyevent 66` & `(540, 1374)` | Enter hoặc nút Tiếp tục |
| **Step 4** | Họ và tên (About You) | `(540, 1026)` | Nhập tên -> `keyevent 4` hạ phím |
| **Step 4** | Tuổi (About You) | `(540, 1310)` | Nhập tuổi -> `keyevent 4` hạ phím |
| **Step 4** | Submit About You | `(540, 1798)` | Bấm Tiếp tục |
| **Màn hình đích** | Xác nhận thành công | `Đã xác minh email` / `auth.openai.com/email-verification` | Chuyển tiếp vào `https://chatgpt.com/` |
