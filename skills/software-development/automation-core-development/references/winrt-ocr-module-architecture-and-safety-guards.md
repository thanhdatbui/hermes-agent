# Kiến trúc Module WinRT OCR và Chốt Chặn An Toàn (automation_core.ocr)

## 1. Bối cảnh & Mục tiêu Kiến trúc
Trong hệ sinh thái Taadaa Farm (78 máy), hai điểm nghẽn lớn nhất của cơ chế đọc giao diện truyền thống (`uiautomator dump` XML) là:
1. **TikTok liên tục đổi obfuscated resource-id:** Nút Follow đổi liên tục từ `id/fds` $\to$ `id/ff8` $\to$ `id/fm9` $\to$ `id/fmp` $\to$ `id/fo4`, khiến parser XML bị mù và phải bảo trì selector liên tục.
2. **Độ trễ dump XML quá lớn (3s – 15s/lần):** Khi máy lag hoặc màn hình đang render animation, dump XML dễ gây timeout đứt gãy nhịp lướt video hoặc chuỗi đăng ký tài khoản.

Giải pháp: Đóng gói module OCR dùng chung `automation_core.ocr` tận dụng engine **WinRT OCR native** của Windows (thông qua `D:\Taadaa\tools\ocr_boxes.ps1`), xử lý ảnh chụp màn hình trong ~0.1s - 0.3s (nhanh gấp 10-20 lần XML).

---

## 2. Các Thành Phần Cốt Lõi Trong `automation_core.ocr`

### A. Chuẩn Hóa Text & Phân Tách Tọa Độ (`norm_text`, `parse_ocr_boxes_output`)
- `norm_text(s: str) -> str`:
  - Chuyển đổi `đ/Đ` thành `d/D`.
  - Phân tách Unicode NFKD và loại bỏ combining accents (dấu thanh/mũ).
  - Chuyển về lowercase và chuẩn hóa khoảng trắng thừa.
- `parse_ocr_boxes_output(raw_stdout: str) -> list[tuple[str, tuple[int, int, int, int]]]`:
  - Phân tích output từ `ocr_boxes.ps1` có định dạng `x1,y1,x2,y2\t<text>`.
  - Sắp xếp các box từ trên xuống dưới, từ trái sang phải theo dòng đọc tự nhiên.

### B. Cầu Nối PowerShell & Xử Lý Ngoại Lệ Chi Tiết (`ocr_screen_boxes`)
- Không nuốt exception âm thầm hay gom chung vào `Exception`:
  - `FileNotFoundError`: Ghi log ERROR khi không tìm thấy executable `powershell`.
  - `subprocess.TimeoutExpired`: Ghi log WARNING kèm thông số timeout khi lệnh OCR bị nghẽn.
  - `OSError`: Ghi log lỗi hệ thống OS cụ thể.
  - `r.returncode != 0`: Kiểm tra mã thoát của PowerShell, log stderr và trả về danh sách rỗng thay vì parse stdout lỗi.

### C. Dập Popup Thần Tốc Kèm Cầu Dao Bảo Mật (`find_popup_dismiss_button_ocr`)
- **Từ khóa dập popup (`POPUP_DISMISS_KEYWORDS`):** `"de sau"`, `"khong phai bay gio"`, `"huy"`, `"dong"`, `"not now"`, `"cancel"`, `"later"`, `"skip"`, `"bo qua"`, `"close"`, `"dismiss"`.
- **Cầu dao an toàn (Sensitive Guard):**
  - Quét toàn bộ text trên màn hình với các từ khóa nhạy cảm: `"dang nhap"`, `"tai khoan"`, `"mat khau"`, `"credential"`, `"password"`, `"payment"`, `"thanh toan"`, `"captcha"`, `"otp"`.
  - **Sử dụng Regex Word Boundary (`\b`):** Chống false positive khi gặp từ ngữ thông thường chứa chuỗi con (ví dụ: *"Cửa hàng Footprint"*, *"Prepayment"* không bị nhầm thành *"payment"*).
  - Nếu phát hiện màn hình nhạy cảm $\rightarrow$ **Lập tức trả về `None`**, tuyệt đối không click bừa vào màn hình thử thách hay đăng nhập.
- **Telemetry:** Ghi nhận `decision=dismiss` (kèm `keyword`) hoặc `decision=reject` (kèm `sensitive_keyword`).

### D. Phân Loại Quan Hệ Profile & Luật Follow Dominance (`classify_profile_action_ocr`)
1. **Luật Follow Dominance (Ưu tiên tuyệt đối):**
   - Trên TikTok, nick chưa follow (hoặc bị nhả follow) hoàn toàn có thể hiển thị song song cả nút đỏ `[Follow]` (hoặc `[Follow lại]`) VÀ nút xám `[Nhắn tin]` (nếu tài khoản mở DM hoặc follow mình trước).
   - Quy tắc: **Chỉ cần xuất hiện bất kỳ nút chưa follow nào (`"follow"`, `"follow lai"`, `"theo doi"`) $\rightarrow$ 100% kết luận `not_followed`**, bất kể có chữ "Nhắn tin" bên cạnh hay không.
2. **Khử bẫy nhãn thống kê (Stat Counter Exclusion):**
   - Cột số liệu dưới avatar luôn chứa nhãn: `"127 Đã follow"`, `"10K Follower"`, `"0 Đang follow"`.
   - CẤM dùng substring check `"follow" in text` vì sẽ nhận nhầm cột số liệu thành nút Follow.
   - Loại trừ triệt để bằng regex `is_stat_counter()`: `follower`, `followers`, `dang follow`, `da follow`.
3. **Khóa độ dài nhãn nút bấm (Text Length Guard):**
   - Nút hành động chuẩn trên TikTok chỉ có từ 1 đến 3 từ.
   - Nếu `len(n_txt.split()) > 3` (ví dụ Bio: *"Follow kênh mình nhé mọi người"*) $\rightarrow$ Lập tức bỏ qua, không nhận diện thành nút bấm.
4. **Phân loại `followed`:**
   - Chỉ trả về `followed` khi KHÔNG CÒN nút follow nào VÀ xuất hiện nút quan hệ đã follow (`"nhan tin"`, `"message"`, `"gui tin nhan"`, `"ban be"`, `"friends"`, `"dang theo doi"`).

### E. Tìm Tọa Độ Nút Follow Kèm Xếp Hạng Ưu Tiên (`find_follow_button_center_ocr`)
- Khi có nhiều box OCR cùng thỏa mãn điều kiện `not_followed`:
  - **Khoảng cách dọc tới tâm (`anchor_y`):** Ưu tiên box có vị trí $y$ gần tâm dải header nhất (`(y_min + y_max) // 2`).
  - **Độ ưu tiên nhãn chuẩn:** Khi khoảng cách dọc bằng nhau, ưu tiên nhãn chính thức `"follow"` (priority 0) trước các nhãn thứ cấp `"follow lai"` / `"theo doi"` (priority 1).

---

## 3. Ma Trận Ứng Dụng Hybrid (XML vs WinRT OCR)

| Tác vụ | Công nghệ ưu tiên | Cơ chế phối hợp |
| :--- | :--- | :--- |
| **Dập Popup che màn hình** | **OCR First-Line (0.3s)** | Quét 0.3s thấy nút đóng là tap ngay. Không thấy mới gọi XML chuyên sâu `benign_popup.py`. |
| **Bấm nút đổi ID (Follow / Đăng ký)** | **XML trước $\to$ OCR Fallback** | Đọc XML theo selector. Nếu TikTok đổi ID ra `unknown` $\to$ OCR nhìn chữ tap cứu nguy, chống timeout. |
| **Định danh UID (@handle), Checkbox, Focus** | **100% XML (CẤM OCR)** | Đảm bảo đối soát chính xác 100%, chống nhầm lẫn OCR (`0` vs `O`, `1` vs `l`). |
