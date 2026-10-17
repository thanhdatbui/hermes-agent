# Pitfall & Canonical Flow: Gõ Tiếng Việt Có Dấu (Unicode/UTF-8) trên Android Farm

## 1. Bản chất vấn đề
- Lệnh `adb shell input text <string>` của Android chỉ hỗ trợ ký tự ASCII chuẩn. Khi đưa chuỗi tiếng Việt có dấu hoặc ký tự đặc biệt, lệnh sẽ:
  - Bị nuốt chữ / văng ký tự rác (mất dấu tiếng Việt).
  - Bị lỗi khoảng trắng `%s` nếu không escape.
  - Làm sai lệch hoàn toàn yêu cầu của Operator (Operator yêu cầu viết có dấu nhưng xuất ra không dấu).

## 2. Giải pháp chuẩn hoá: AdbKeyboard Base64 Broadcast

Trên toàn bộ Samsung S7 và các máy Android thuộc Taadaa Farm, bàn phím `com.github.uiautomator/.AdbKeyboard` đã được cài đặt sẵn. Để gõ tiếng Việt có dấu chính xác 100%:

### Quy trình 5 bước bắt buộc:

```python
import base64
import time

# Bước 1: Kích hoạt và đặt default IME sang AdbKeyboard
dev.shell(['ime', 'enable', 'com.github.uiautomator/.AdbKeyboard'])
dev.shell(['ime', 'set', 'com.github.uiautomator/.AdbKeyboard'])
time.sleep(0.5)

# Bước 2: Tap focus vào ô EditText cần nhập
dev.shell(['input', 'tap', str(cx), str(cy)])
time.sleep(0.5)

# Bước 3: Xoá sạch text cũ bằng broadcast hoặc backspaces
dev.shell(['am', 'broadcast', '-a', 'ADB_KEYBOARD_CLEAR_TEXT'])
time.sleep(0.5)
# Backup backspace nếu ô input không ăn broadcast clear
dev.shell(['input', 'keyevent', *(['67'] * 15)])
time.sleep(0.5)

# Bước 4: Encode UTF-8 chuỗi có dấu sang Base64 và phát broadcast
text_with_accents = "Đi tập cùng tui và làm đồ ăn healthy mỗi ngày! 🥗"
b64_payload = base64.b64encode(text_with_accents.encode("utf-8")).decode("ascii")

# Broadcast chuẩn của AdbKeyboard trên farm (bắt buộc đúng action name)
dev.shell(['am', 'broadcast', '-a', 'ADB_KEYBOARD_INPUT_TEXT', '--es', 'text', b64_payload])
time.sleep(1.0)

# Bước 5: Bấm Lưu / Xác nhận và kiểm tra read-back qua XML / WinRT OCR
```

## 3. Các bẫy thường gặp (Pitfalls)
1. **Nhầm action broadcast:**
   - Dùng `ADB_INPUT_B64` / `ADB_CLEAR_TEXT`: một số phiên bản AdbKeyboard cũ không bắt được action này.
   - Action chuẩn đã test thành công trên toàn farm: `ADB_KEYBOARD_INPUT_TEXT` với param `--es text <base64>` và `ADB_KEYBOARD_CLEAR_TEXT`.
2. **Quên bật IME trước khi broadcast:**
   - Nếu IME hiện tại đang là SamsungKeypad / XwIME, broadcast vào AdbKeyboard sẽ không có tác dụng trên giao diện. Phải gọi `ime set com.github.uiautomator/.AdbKeyboard` trước.
3. **Kỷ luật người dùng (User Invariant):**
   - Khi Operator yêu cầu "viết có dấu" hoặc "chuẩn hoá tiếng Việt": TUYỆT ĐỐI KHÔNG dùng `input text` không dấu đối phó. Phải dùng AdbKeyboard UTF-8 Base64 ngay từ bước đầu.
