# Kỹ Thuật Gõ Tiếng Việt Có Dấu Qua AdbKeyboard & Cơ Chế Ghim Video TikTok LIFO

## 1. Gõ Tiếng Việt Có Dấu Qua ADB Trên Android Farm (Samsung S7 / Android 8)

### Vấn Đề Hiện Trường
- Lệnh chuẩn `adb shell input text` chỉ nhận tập ký tự ASCII (tiếng Việt không dấu). Khi truyền chuỗi có dấu UTF-8 (ví dụ: `Học sinh ngoan nhưng hơi bất ổn`), shell Android sẽ drop ký tự hoặc nuốt chữ (`Hoc ys`, `Hoc sin`).
- Các action broadcast phỏng đoán như `ADB_INPUT_B64` hay `ADB_INPUT_TEXT` không được `com.github.uiautomator/.AdbKeyboard` đăng ký trong IntentFilter, dẫn đến broadcast không có tác dụng.

### Quy Trình Chuẩn Xác O(1)
1. **Focus ô nhập liệu:** Tap vào tọa độ ô `EditText` để hiển thị con trỏ soạn thảo.
2. **Xóa sạch text cũ:**
   - Dùng phím tắt chọn tất cả và xóa: `input keyevent --meta 113 29 && input keyevent 67` (Ctrl+A rồi Del).
   - Dự phòng: Tap cuối ô (`input keyevent 123`) và gửi chuỗi backspace (`input keyevent 67 ...`).
3. **Kích hoạt AdbKeyboard:**
   ```bash
   adb shell ime enable com.github.uiautomator/.AdbKeyboard
   adb shell ime set com.github.uiautomator/.AdbKeyboard
   ```
4. **Mã hóa Base64 và Broadcast:**
   - Mã hóa chuỗi UTF-8 tiếng Việt sang Base64 chuẩn ASCII.
   - Gửi broadcast với **Action chính xác: `ADB_KEYBOARD_INPUT_TEXT`** và **Extra key: `text`**:
   ```bash
   adb shell am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <BASE64_STRING>
   ```
5. **Khôi phục bàn phím hệ thống:**
   - Đổi lại bàn phím mặc định: `adb shell ime set com.sec.android.inputmethod/.SamsungKeypad`.
6. **Lưu & Nghiệm thu:**
   - Tap nút Lưu (`Lưu` / `Save`).
   - Chụp ảnh màn hình và chạy WinRT OCR đối soát để đảm bảo chữ có dấu hiển thị sắc nét 100%.

---

## 2. Cơ Chế Ghim Video TikTok Profile (LIFO - Last In First Out)

### Cơ Chế Sắp Xếp
- Trên TikTok (phiên bản v47+), video được ghim theo cơ chế **LIFO (Last In First Out)**:
  * Video nào được bấm **Ghim sau cùng** sẽ được đẩy lên **Vị trí số 1 (Ngoài cùng bên trái của Hàng 1)**.
  * Các video ghim trước đó sẽ bị đẩy dần sang bên phải (Vị trí số 2 ở giữa và Vị trí số 3 bên phải).

### Kịch Bản Tối Ưu Mỏ Neo Uy Tín (Social Proof)
- Khi một kênh có 3 video ghim (ví dụ: `22K` - `4.4K` - `5.2K`), điểm nhìn đầu tiên của người xem theo chuẩn F-pattern luôn là ô trên cùng bên trái (Vị trí số 1).
- Nếu video to nhất (`22K`) đang đứng ở giữa hoặc bên phải do bị video ghim mới đẩy sang:
  1. Gọi lệnh **Bỏ ghim (UNPIN)** video `22K`.
  2. Ngay sau đó gọi lệnh **Ghim lại (PIN)** chính video `22K`.
  👉 TikTok sẽ lập tức đẩy video `22K` lên đứng đầu tiên ngoài cùng bên trái: `[22K] (Trái) — [4.4K] (Giữa) — [5.2K] (Phải)`.
