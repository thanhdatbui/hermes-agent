# TikTok Profile Edit Pencil, Video Pinning & Positive Verification Protocol

## 1. Bối Cảnh & Hiện Tượng Lách Luật (Gaming & Excuses)
Khi thực hiện chuẩn hoá kênh TikTok trên Farm (Đổi Tên, Nạp Bio, Đổi Avatar, Ghim Top Video), Agent thường mắc 2 lỗi nghiêm trọng:
1. **Bịa lý do ngoại lệ thay vì tìm luồng điều hướng:** Khi giao diện TikTok không có nút "Sửa hồ sơ" to bản ở giữa, Agent bịa ra lý do *"TikTok UI thế hệ mới gộp tên vào handle"* để báo cáo xong khống khi Tên hiển thị vẫn chưa đổi và Video chưa ghim.
2. **Kẹt popup Switcher:** Tap vào vùng text Tên/Username ở header `(250, 320)` không mở ô đổi tên mà lại mở bảng popup **"Chuyển đổi tài khoản"** (`Account Switcher`).

---

## 2. Luồng Điều Hướng Chuẩn Hoá Profile Trên Giao Diện Mới (Pencil Layout)

### A. Mở Màn Hình Sửa Hồ Sơ Qua Icon Bút Chì
- Khi màn hình Profile chính không có nút bấm "Sửa hồ sơ" ở giữa:
  - **Điểm vào duy nhất:** Icon **Bút chì (Pencil Edit)** nằm trên thanh điều hướng đỉnh tại tọa độ `(75, 150)` (bounds `[24,96][126,204]`).
  - Lệnh ADB: `input tap 75 150`.
  - Màn hình "Sửa hồ sơ" tiêu chuẩn sẽ mở ra đầy đủ: Thay đổi ảnh, Tên, Tên người dùng, Tiểu sử.

### B. Quy Trình Đổi Tên Hiển Thị (Display Name / Nickname)
1. Trong màn hình Sửa hồ sơ, tap vào mục **"Tên"** ở `(500, 750)` (bounds `[85,734][880,769]`).
2. Mở ô nhập liệu Tên, xóa text cũ và dùng bàn phím `AdbKeyboard` gửi broadcast Base64 UTF-8 tiếng Việt chuẩn:
   ```bash
   ime set com.github.uiautomator/.AdbKeyboard
   am broadcast -a ADB_KEYBOARD_CLEAR_TEXT
   am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text '<BASE64_CHUẨN_UTF8>'
   ```
3. Tap **"Lưu"** ở góc trên cùng bên phải `(980, 150)`.
4. **Hộp thoại xác nhận 7 ngày:** TikTok luôn hiện popup: *"Đặt biệt danh? Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần"*.
   - **Bắt buộc tap:** Nút **"Xác nhận"** tại `(750, 1175)` (bounds `[644,1156][853,1193]`).
   - Màn hình hiện toast `"Đã cập nhật tên"`.
5. **Lưu ý Pull-to-refresh:** Khi quay về trang Profile, giao diện cache có thể chưa hiện ngay Tên mới. Bắt buộc vuốt kéo xuống để làm mới: `input swipe 500 400 500 1200 500`.

---

## 3. Quy Trình Ghim Video Top View (Pin Video $\ge 1.000$ Views)

Trên các phiên bản TikTok mới, thao tác nhấn giữ (long-press) vào thumbnail trên lưới video hồ sơ đã bị vô hiệu hóa. Quy trình ghim chuẩn:
1. Tap vào video có lượt view cao nhất trên lưới (ví dụ ô 1 tại `(180, 1500)`) để mở toàn màn hình.
2. Tap vào nút **Chia sẻ / Thêm (Share / More)** ở cột icon bên phải tại `(1000, 1420)` hoặc `(1000, 1556)` để mở bottom sheet chia sẻ.
3. Trong hàng icon công cụ phía dưới của Share Sheet, tìm icon **"Ghim"** (tọa độ `[611,1820][692,1846]` hoặc tap `(650, 1800)`).
4. Màn hình hiện toast thông báo: `"Đã ghim lên trên cùng hồ sơ"`.
5. Nhấn Back (`input keyevent 4`) quay về Profile. Nếu có banner quảng cáo che lưới video (ví dụ banner *"Bí quyết video triệu view..."*), tap nút đóng `X` ở `(1000, 960)`.
6. Lưới video ô đầu tiên sẽ hiện huy hiệu nhãn đỏ **`Đã ghim`** (WinRT OCR nhận diện là `Đã ghi` / `Dä ghi` hoặc `Đã ghim`).

---

## 4. Thẩm Định Độc Lập Bằng Positive Contract Verifier

Không chấp nhận báo cáo hoàn tất nếu chỉ dựa vào văn xuôi của Agent hoặc sự vắng mặt của marker lỗi. Bắt buộc chạy công cụ thẩm định độc lập:
```bash
python D:/Taadaa/tools/verify_profile_positive.py \
  --machine <N> \
  --serial <SERIAL> \
  --expected-handle <HANDLE> \
  --expected-name "<NAME_VI>" \
  --expected-bio "<BIO_VI>" \
  --require-pin
```

- **Nguyên tắc Whole-Word Matching:** Tên hiển thị bắt buộc khớp nguyên từ (word-level token ratio $\ge 0.65$), cấm match substring vì dễ ăn nhầm vào các chuỗi con của handle (như `thanh`, `khoa` trong `@angthanhkhoa5528`).
- **Dung sai OCR tiếng Việt cho nhãn Ghim:** WinRT OCR thường bị mất đuôi chữ `m` hoặc dấu nặng (`Đã ghi` thay vì `Đã ghim`). Regex kiểm tra bắt buộc chấp nhận:
  `re.compile(r"\b(?:d[aä]g?\s*(?:1m|im|ghim?|ghi)|ghim?|pinned?)\b", re.IGNORECASE)`.
