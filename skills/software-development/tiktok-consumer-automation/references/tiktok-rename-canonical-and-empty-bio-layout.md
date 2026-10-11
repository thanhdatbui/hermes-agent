# TikTok Nickname Rename Canonical & Empty-Bio Layout Handling (2026-10-11)

## 1. Kỷ Luật Zero Re-invent: Cấm Clone Script Đổi Tên Riêng Theo Máy
- **Hiện tượng bị user phạt:** Cứ mỗi lần đổi tên trên máy bất kỳ (M8, M20, M44, M46, M71, M76), agent lại copy sinh ra một file script mới `D:/Taadaa/tools/do_rename_m<ID>.py` và một file test `tests/test_do_rename_m<ID>.py`.
- **Hậu quả:** Gây over-engineering nghiêm trọng, tốn ngân sách tool calls để debug các lỗi lặp lại (device lock, OCR matcher, timeout), làm user khó chịu: *"Ngày nào tao cũng đổi tên mà cứ đi viết lại code đổi tên chi vậy"*.
- **Quy chuẩn bắt buộc:**
  1. Sử dụng canonical runner tham số hóa, truyền machine ID, username mục tiêu và tên mới:
     ```bash
     python D:/Taadaa/tools/do_rename.py --machine <ID> --serial <SERIAL> --user <USERNAME> --name "<NEW_NAME>"
     ```
  2. Subagent điều phối thực thi nhiệm vụ đổi tên BẮT BUỘC chạy **AG Gemini Pool (`ag-gemini-pool-3`)**, Luna chỉ dùng làm fallback khi Gemini nghẽn mạng/rate-limit.

---

## 2. Dị Biệt Giao Diện TikTok v47+: Tài Khoản Chưa Có Bio (Empty Bio)

### A. Triệu Chứng Hiện Trường
Trên phiên bản TikTok mới (v47.x), tài khoản cá nhân có 2 layout hoàn toàn khác nhau:
1. **Layout đã hoàn tất hồ sơ (có Bio hoặc Creator/Shop):**
   - Dưới thông số Follower/Thích có nút to rõ ràng: `Sửa hồ sơ` (`[60, 840, 360, 890]`) hoặc icon cây bút chì ở góc trên bên trái `(72, 148)`.
2. **Layout tài khoản mới / chưa có bio (Empty Bio - ví dụ Máy 44 `@annapmfdh0a`):**
   - ẨN HOÀN TOÀN nút `Sửa hồ sơ` và icon cây bút chì.
   - Góc trên bên trái `(72, 148)` là icon **Tìm bạn bè** (Person with +).
   - Nút duy nhất nằm chính giữa dưới thông số là **`+ Thêm tiểu sử`** (`id/t6g` tại `(540, 867)`).

### B. Cạm Bẫy Phổ Biến (Anti-Patterns)
1. **Bấm nhầm bút chì cũ `(72, 148)`:** Mở ra popup *"Tìm bạn bè trong danh bạ"* $\rightarrow$ State machine nhận nhầm là `UNKNOWN` rồi ấn Back $\rightarrow$ rơi vào loop vô tận.
2. **Bấm nhầm dòng Tên ở giữa `(540, 560)`:** Trên layout này, dòng Tên có icon mũi tên mở **Chuyển đổi tài khoản (Account Switcher)** $\rightarrow$ tap vào đây làm hiện menu đổi nick $\rightarrow$ script kẹt ở trạng thái `SWITCHER`.
3. **Lỗi OCR nhận diện "tiểu sử":** WinRT OCR thường đọc chữ `Tiểu sử` thành `TiéU sd`. Nếu regex chỉ bắt `tieu su`, state machine sẽ phân loại nhầm màn Bio thành `UNKNOWN` và ấn Back thoát ra.

### C. Giải Pháp Điều Hướng Chuẩn Xác
1. **Mở rộng regex nhận diện Bio:**
   ```python
   re.search(r"ti[eé]u\s*s[uưd]|thay d\w{0,3} anh", normalized_text)
   ```
2. **Luồng xử lý khi chỉ thấy `+ Thêm tiểu sử`:**
   - Tap vào nút `+ Thêm tiểu sử` tại `(540, 867)`.
   - Nhập một bio ngắn phù hợp với chủ đề kênh (ví dụ: kênh thú cưng $\rightarrow$ nhập `"Kênh mèo Mi Mi"`) và bấm `Lưu`.
   - Sau khi lưu bio, giao diện Hồ sơ của TikTok sẽ lập tức cập nhật, **kích hoạt hiển thị nút chuẩn `Sửa hồ sơ`**.
   - Tiếp tục tap vào `Sửa hồ sơ` $\rightarrow$ chọn dòng `Tên` (biệt danh) $\rightarrow$ nhập Tên mới qua AdbKeyboard $\rightarrow$ `Lưu` và `Xác nhận`.
