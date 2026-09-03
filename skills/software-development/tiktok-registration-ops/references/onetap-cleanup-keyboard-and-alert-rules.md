# Quy tắc Vận hành Reg TikTok, Bàn phím IME & Xử lý Session rác

## 1. Quy tắc Gửi Ảnh Báo Cáo Farm (Farm Alert Banner)
* **BẮT BUỘC chèn Banner Đỏ vào đầu ảnh:** Mọi ảnh chụp màn hình máy farm khi báo cáo lỗi cho user / gửi Telegram phải có banner đỏ với format:
  `[MAY X] - HH:MM:SS dd/mm` (Ví dụ: `[MAY 11] - 19:50:58 24/08`).
* **Cấm gửi ảnh trơn không số máy:** Không gửi ảnh raw không có định danh số máy.
* **Bảo toàn hiện trường máy lỗi:** Máy lỗi BẮT BUỘC giữ nguyên màn hình hiện tại + giữ `device-locks` (`status=handoff` hoặc `locked_by_user_reg_flow`). Cấm tự ý `force-stop` hoặc bấm `KEYCODE_HOME` làm mất dấu vết lỗi trước khi user hướng dẫn.

---

## 2. Chuẩn hóa Bàn phím ADB Keyboard (`com.github.uiautomator/.AdbKeyboard`)
* **Nguyên nhân lỗi SamsungKeypad:** Bàn phím mặc định Samsung không nhận Unicode tiếng Việt từ broadcast ADB, hay làm bật popup hệ thống *"Chọn bàn phím"* che mất nút bấm, và dễ gây nhập nhầm số máy vào ô tên.
* **Quy chuẩn toàn farm:** Ngoại trừ repo `register gmail` (cần SamsungKeypad để bypass Google Play bot-check), tất cả các luồng automation khác (`Tiktok_Reg`, `tiktok-log-in`, `Hotmail`, `add mail khoi phuc`...) BẮT BUỘC chuyển sang dùng `AdbKeyboard`:
  ```bash
  adb shell ime enable com.github.uiautomator/.AdbKeyboard
  adb shell ime set com.github.uiautomator/.AdbKeyboard
  ```
* **Nhập text / Tiếng Việt có dấu / Mật khẩu:** Gửi chuỗi qua broadcast base64 UTF-8:
  ```python
  import base64
  encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
  shell(device_id, "am", "broadcast", "-a", "ADB_KEYBOARD_INPUT_TEXT", "--es", "text", encoded)
  ```

---

## 3. Module Xử lý Màn hình Đăng nhập nhanh One-Tap ("Tiếp tục với tên @...")
* **Điều kiện xóa session rác:** Khi gặp màn hình đăng nhập nhanh "Tiếp tục với tên @username", script **BẮT BUỘC đối chiếu với toàn bộ kho Excel** (`Tik1` -> `Tik4`, `taikhoan_dat_v2_updated`, `taikhoan_run_safe`, `gmail_clean_v2`):
  * **Nếu nick CÓ trong kho Excel:** Giữ nguyên, không xóa.
  * **Nếu nick KHÔNG có trong bất kỳ file Excel nào:** Đây là session rác cũ lưu trong cache app -> Bấm menu 3 chấm góc phải trên (`Khác` / `More`) -> Chọn **"Xóa tài khoản"** -> Bấm **"Xóa"** xác nhận.
* Sau khi xóa (hoặc nếu giữ lại), bấm **"Sử dụng tài khoản khác"** ở đáy màn hình để vào luồng đăng ký mới.

---

## 4. Quy tắc Đặt Tên Tiếng Việt & Báo Cáo
* Tên hiển thị TikTok bắt buộc lấy tên tiếng Việt gần âm từ prefix email (qua map `_VI_NAME_MAP`) hoặc random từ pool fallback tiếng Việt chuẩn (`_VI_NAME_FALLBACK`).
* Tuyệt đối không để trống ô tên hoặc để tên bị dính ký tự số đơn lẻ.
* Báo cáo kết quả đăng ký cho user phải nêu rõ: **STT máy, TikTok ID (@handle), Tên tiếng Việt hiển thị, Email đăng ký, Folder/Slot mapping**.
