# TikTok Profile Rename (Display Name / Nickname) via OCR State Machine (Samsung Galaxy S7 Farm)

## Bối cảnh & Vấn đề Kỹ thuật
- **Lỗi `uiautomator dump` trên Samsung Galaxy S7 (SM-G930F/W8, Android 7/8):** Khi chạy TikTok, tiến trình `uiautomator` hệ thống thường xuyên bị quá tải, treo hoặc bị OOM killer tiêu diệt với exit code `137`.
- **`atx-agent` /dump/hierarchy:** Trên một số máy, `atx-agent` chỉ dump được status bar hệ thống mà không thấy cây node của TikTok, hoặc trả về XML rỗng/stale.
- **Giải pháp chuẩn hóa (Battle-Tested):** Sử dụng State Machine kết hợp **Native WinRT OCR** (`tools/ocr_boxes.ps1`) để nhận diện màn hình và tọa độ động theo thời gian thực (như đã áp dụng thành công trên `do_rename_m8.py` và `do_rename_m20.py`).

---

## 1. Tọa độ & Hình học UI trên Samsung Galaxy S7 (1080x1920)

| Vị trí / Thao tác | Tọa độ chuẩn S7 (X, Y) | Ghi chú |
|---|---|---|
| **Tab Hồ sơ (Profile Tab)** | `(972, 1857)` | Góc dưới bên phải thanh điều hướng bottom bar |
| **Cuộn Header Hồ sơ** | `(540, 1100)` → `(540, 600)` | Vuốt nhẹ để ghim username lên sticky header |
| **Ghim ID / Mở Switcher** | `(500, 140)` | Tap username trên header mở sheet 'Chuyển đổi tài khoản' |
| **Cuộn Sheet Switcher** | `(540, 1500)` → `(540, 900)` | Khi máy có 8 acc, cuộn lên để thấy 4 acc phía dưới |
| **Nút Sửa hồ sơ** | `(72, 148)` hoặc `find_box("sua ho s")` | Icon cây bút top-left hoặc nút chữ 'Sửa hồ sơ' |
| **Hàng 'Tên' (Nickname)** | `(600, 752)` | Hàng đầu tiên trong 'Sửa hồ sơ', nằm trên 'Tên người dùng' |
| **Nút Xóa tên cũ (X)** | `(960, 576)` | Nút clear trong ô nhập Tên |
| **Nút 'Lưu' (Save)** | `(980, 140)` | Góc trên bên phải header màn sửa Tên |
| **Nút 'Hủy' (Cancel)** | `(90, 150)` | Góc trên bên trái header màn sửa Tên |
| **Nút 'Xác nhận' popup** | `(750, 1100)` | Popup cảnh báo đổi tên 7 ngày |

---

## 2. HARD SAFETY GATE: 'Tên' (Nickname) vs 'Tên người dùng' (Username)

### Giới hạn chính sách TikTok:
* **Tên (Nickname / Display Name):** Giới hạn đổi **1 lần mỗi 7 ngày**. Nằm ở hàng đầu tiên (`y ≈ 730–769`).
* **Tên người dùng (Username / @handle):** Giới hạn đổi **1 lần mỗi 30 ngày**. Nằm ở hàng thứ hai (`y > 850`).

### CẠM BẪY TỬ HUYỆT & CHỐT CHẶN BẮT BUỘC:
1. **Tuyệt đối CẤM tap vào hàng Tên người dùng:**
   Script bắt buộc phải có chốt chặn kiểm tra hình học giữa box nhãn 'Tên' (`ten_box`) và 'Tên người dùng' (`user_box`):
   ```python
   xy = (XY_NAME_ROW[0], center(ten_box)[1]) if ten_box else XY_NAME_ROW
   if user_box and xy[1] > user_box[1] - 30:
       raise Abort(f"Điểm tap Tên {xy} không nằm trên 'Tên người dùng' (y={user_box[1]}) -> dừng ngay!")
   ```
2. **Nhận diện và thoát ngay màn `USERNAME_EDIT`:**
   Nếu OCR phát hiện màn hình có các dấu hiệu: bộ đếm `\d{1,2}/24`, text `mỗi 30 ngày`, `chữ cái, chữ số`, `tiktok.com/@...` mà **KHÔNG** có `Tiểu sử` / `Thay đổi ảnh`:
   $\rightarrow$ Đây là màn sửa Username! Script phải lập tức bấm `keyevent 4` (Back), **TUYỆT ĐỐI KHÔNG gõ bất kỳ ký tự nào** vào ô này.

---

## 3. Quy trình Nhập liệu & Nghiệm thu An toàn

1. **Nhập text tiếng Việt qua AdbKeyboard:**
   - Xóa chữ cũ: Tap nút X `(960, 576)` kết hợp broadcast `ADB_KEYBOARD_CLEAR_TEXT`.
   - Set bàn phím: `ime set com.github.uiautomator/.AdbKeyboard`.
   - Encode Base64 chuỗi UTF-8:
     ```python
     encoded = base64.b64encode(new_name.encode("utf-8")).decode("ascii")
     shell("am", "broadcast", "-a", "ADB_KEYBOARD_INPUT_TEXT", "--es", "text", encoded)
     ```
2. **Pre-Save Verification Gate:**
   - Sau khi gõ, chụp lại OCR màn hình để kiểm tra:
     * Nội dung ô nhập khớp `new_name` (chuẩn hóa không dấu `norm(l) == new_name_norm`).
     * Bộ đếm ký tự khớp `{len(new_name)}/30` (ví dụ `11/30` cho "Phương Thảo", `6/30` cho "Hải Sa").
   - **Chỉ bấm 'Lưu' đúng 1 lần duy nhất** khi cả 2 điều kiện trên đều thỏa mãn. Nếu không khớp, bấm 'Hủy' `(90, 150)` và Abort, không bấm Lưu bừa bãi.
3. **Xử lý Popup Xác nhận 7 ngày:**
   - TikTok sẽ hiện dialog: *"Đặt biệt danh? Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần"*.
   - Tap nút 'Xác nhận' `(750, 1100)` hoặc box OCR khớp `xac nhan | confirm | dong y`.
4. **Nghiệm thu OCR trên Profile root:**
   - Sau khi bấm Lưu và xác nhận, Back về trang Hồ sơ (`PROFILE`).
   - Đọc chính xác dòng text nằm ngay phía trên `@username` (theo tọa độ `b2[3] <= b[1] + 5 and b[1] - b2[3] < 120`).
   - Bằng chứng nghiệm thu hợp lệ bắt buộc gồm:
     * Full screenshot 1080x1920 (`MEDIA:<path>.png`).
     * JSON report (`target_user`, `new_name`, `final_name_ocr`, `verified_by_ocr=True`).

---

## 4. Quy tắc Sinh Tên Tiếng Việt Tự Nhiên (User Directives)

- **CẤM dùng nguyên username/email prefix tiếng Anh dài:** (ví dụ `francesuhuntertgxg5`, `LilyanLederhos64090` $\rightarrow$ quá dài, thô, lộ bot).
- **Quy tắc rút gọn & chế tên Việt gần âm:**
  * `frances-` / `florence-` $\rightarrow$ **Phương Thảo**, **Thu Phương**, **Phương**.
  * `sadou-` $\rightarrow$ **Hải Sa**, **Sa**.
  * `lilyan-` $\rightarrow$ **Linh**, **Liên**.
  * `kylar-` $\rightarrow$ **Kỳ La**.
- **Phong cách đặt tên người thật (`make_tiktok_name` trong `social_reg_v1.py`):**
  * Họ + Đệm + Tên (25%): *Trần Minh Đạt, Nguyễn Hoài An*
  * Họ + Tên (25%): *Lê Linh, Vũ Nam*
  * Đệm + Tên (20%): *Ngọc Linh, Thanh Thảo, Khánh Vy*
  * Tên + Biệt danh đời thường (20%): *Linh Bông, Đạt Còi, Vy Miu, An Kem*
  * Tên lặp / Duo dễ thương (10%): *An An, Gạo Gạo, Miu Miu*

---

## 5. Device Lock Integration

- Toàn bộ script đổi tên bắt buộc phải acquire device lock:
  ```python
  from automation_core.device_lock import operator_device_lock

  with operator_device_lock(machine=machine_id, serial=serial, project="do_rename", timeout=300):
      # Thực thi flow an toàn, tự động restore default IME khi hoàn tất
  ```
- Tránh xung đột tuyệt đối với các cron nuôi acc (feed/follow/upload) đang chạy trên farm.
