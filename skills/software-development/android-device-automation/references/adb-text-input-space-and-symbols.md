# Quy Chuẩn Nhập Văn Bản, Khoảng Trắng và Ký Tự Đặc Biệt Qua ADB (Input Text & Keyevent)

## 1. Bản chất cơ chế `adb shell input text` trên Android
- Lệnh `/system/bin/input text <string>` trên Android phân rã chuỗi tham số theo khoảng trắng (whitespace/space).
- Khi truyền chuỗi chứa dấu cách trực tiếp (ví dụ: `/system/bin/input text "Hoang Tuoc"`), Android shell nhận thành 3 arguments (`argv[1]=text`, `argv[2]=Hoang`, `argv[3]=Tuoc`).
- Binary `/system/bin/input` yêu cầu đúng 1 tham số `<string>`. Khi thừa arguments, lệnh báo lỗi `Error: Invalid arguments for command: text` và hủy toàn bộ chuỗi -> Trường nhập liệu (First Name/Last Name, Tên tài khoản) bị bỏ trống (`text=""`), dẫn đến lỗi form validation (như *"Hãy nhập tên"* / `STILL_ON_NAME`).

## 2. Quy tắc mã hóa khoảng trắng (`%s`)
- Để gõ dấu cách hợp lệ qua `input text`, **BẮT BUỘC** thay thế mọi ký tự `' '` thành `'%s'`.
- Android `Input.sendText` sẽ tự động parse chuỗi `%s` thành ký tự dấu cách thực tế khi gửi event vào InputConnection của EditText/WebView.
- Ví dụ: `input text Hoang%sTuoc` -> Text được gõ trên UI: `"Hoang Tuoc"`.

## 3. Quy tắc xử lý ký tự đặc biệt & Bảng Keyevent
Khi không dùng AdbKeyboard broadcast mà dùng native ADB commands:
- **Ký tự `@`**: Gửi qua `input keyevent 77` (`KEYCODE_AT`).
- **Ký tự `#`**: Gửi qua `input keyevent 18` (`KEYCODE_POUND`) (tránh bị shell hiểu là comment).
- **Dấu cách `' '`**: Trong luồng `human_type`, gửi qua `input keyevent 62` (`KEYCODE_SPACE`).
- **Ký tự đặc biệt của Shell (`\`, `$`, `&`, `*`, `(`, `)`, `;`, `'`, `"`, `<`, `>`, `|`, `~`, `^`, `!`, `?`)**: Phải escape bằng tiền tố `\` (ví dụ: `input text "\$"` hoặc `input text "\&"`).

## 4. Code Pattern Chuẩn Cho Helper `input_text` & `human_type`

```python
import random
import re
import time

def input_text(device_id, text):
    """
    Input text qua ADB shell input text.
    Khoảng trắng được encode thành '%s' để tránh lỗi 'Invalid arguments for command: text'.
    Ký tự @ xử lý riêng bằng KEYCODE_AT (77), # bằng KEYCODE_POUND (18).
    """
    if not text:
        return
    tokens = re.split(r'([@#])', str(text))
    for tok in tokens:
        if not tok:
            continue
        if tok == '@':
            shell(device_id, "input", "keyevent", "77")  # KEYCODE_AT
            time.sleep(0.3)
        elif tok == '#':
            shell(device_id, "input", "keyevent", "18")  # KEYCODE_POUND
            time.sleep(0.3)
        else:
            encoded = tok.replace(" ", "%s")
            shell(device_id, "input", "text", encoded)
            time.sleep(0.4)

def human_type(device_id, text):
    """
    Gõ từng ký tự với random delay 60-220ms mô phỏng người thật.
    - Ký tự ' ' (dấu cách): gửi keyevent 62 (KEYCODE_SPACE)
    - Ký tự @: gửi keyevent 77 (KEYCODE_AT)
    - Ký tự #: gửi keyevent 18 (KEYCODE_POUND)
    - Ký tự đặc biệt shell: escape bằng \\
    """
    if not text:
        return
    shell_escapes = set(r"\$&*();'\"<>|~^!?")
    for ch in text:
        if ch == ' ':
            shell(device_id, "input", "keyevent", "62")  # KEYCODE_SPACE
        elif ch == '@':
            shell(device_id, "input", "keyevent", "77")  # KEYCODE_AT
        elif ch == '#':
            shell(device_id, "input", "keyevent", "18")  # KEYCODE_POUND
        elif ch in shell_escapes:
            shell(device_id, "input", "text", f"\\{ch}")
        else:
            shell(device_id, "input", "text", ch)
        time.sleep(random.uniform(0.06, 0.22))
    time.sleep(random.uniform(0.4, 0.8))
```

## 5. Danh sách ký tự an toàn cho bộ sinh mật khẩu (Password Entropy)
- Để đảm bảo 100% tài khoản tương thích với cả Samsung Keyboard, Gboard, WebView Google và ADB shell, chỉ dùng tập ký tự đặc biệt: `["@", "#", "!", "$"]`.
- Tuyệt đối không dùng `%` đơn lẻ ở cuối mật khẩu nếu chưa qua escape layer (do `%` là tiền tố escape của Android input text).
