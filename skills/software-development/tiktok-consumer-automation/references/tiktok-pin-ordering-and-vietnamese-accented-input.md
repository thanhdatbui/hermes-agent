# TikTok Profile Optimization: Pin Ordering & Vietnamese Accented Bio Input

## 1. Cơ Chế Thứ Tự Video Ghim (Pin Grid Ordering) Trên TikTok v47+ (Android 8)
- **Cơ chế LIFO (Last-In, First-Out):**
  - Khi ghim một video mới hoặc ghim lại một video có sẵn, TikTok **luôn đẩy video được ghim sau cùng lên VỊ TRÍ SỐ 1 (Ngoài cùng bên trái của hàng 1)**.
  - Các video ghim trước đó sẽ bị đẩy lần lượt sang phải: `Vị trí 1 cũ -> Vị trí 2 (Ở giữa)`, `Vị trí 2 cũ -> Vị trí 3 (Bên phải)`.
  - Hàng 1 có tối đa 3 video ghim: `[Vị trí 1 (Trái)] - [Vị trí 2 (Giữa)] - [Vị trí 3 (Phải)]`.
- **Chiến lược đưa video hot nhất (view cao nhất) lên vị trí số 1 (Mỏ neo uy tín):**
  - Để đưa video top 1 view lên vị trí ngoài cùng bên trái:
    1. Nhả ghim video top 1 (`UNPIN`).
    2. Ngay sau đó ghim lại video top 1 (`PIN`).
    3. Video top 1 view sẽ lập tức nhảy lên vị trí số 1 ngoài cùng bên trái.
  - Bắt buộc kiểm tra lại thứ tự thực tế qua WinRT OCR / Vision theo từng cột, cấm đoán mò thứ tự.

## 2. Nhập Văn Bản Tiếng Việt Có Dấu Chuẩn Xác Qua ADB (Vietnamese Accented Text Input)
- **Vấn đề kỹ thuật trên dàn máy Samsung S7 (Android 8):**
  - `adb shell input text` chỉ hỗ trợ ASCII thuần (tiếng Việt không dấu). Nếu truyền ký tự UTF-8 có dấu qua lệnh này, shell sẽ nuốt chữ hoặc gây văng / drop ký tự.
  - Các phương thức clipboard thường bị hạn chế quyền trên các Activity sửa hồ sơ TikTok.
- **Giải pháp chuẩn hóa (Canonical Pattern):**
  - Sử dụng module `AdbKeyboard` (`com.github.uiautomator/.AdbKeyboard`) kết hợp Intent Broadcast Base64:
    ```python
    import base64
    from automation_core.adb import AdbClient

    dev = AdbClient(serial=device_serial)
    
    # 1. Focus ô EditText và xóa sạch chữ cũ
    dev.shell(['input', 'tap', str(box_x), str(box_y)])
    dev.shell(['input', 'keyevent', '--meta', '113', '29'])  # Ctrl + A
    dev.shell(['input', 'keyevent', '67'])                  # Backspace
    dev.shell(['input', 'keyevent', '123'])                 # End
    dev.shell(['input', 'keyevent'] + ['67'] * 60)          # Backspaces dự phòng

    # 2. Bật và gán AdbKeyboard làm IME hiện tại
    dev.shell(['ime', 'enable', 'com.github.uiautomator/.AdbKeyboard'])
    dev.shell(['ime', 'set', 'com.github.uiautomator/.AdbKeyboard'])

    # 3. Mã hóa Base64 văn bản UTF-8 và broadcast
    text_utf8 = "Học sinh ngoan nhưng hơi bất ổn - Follow tui nha!"
    b64_msg = base64.b64encode(text_utf8.encode('utf-8')).decode('ascii')
    dev.shell(['am', 'broadcast', '-a', 'ADB_KEYBOARD_INPUT_TEXT', '--es', 'text', b64_msg])

    # 4. Trả IME về bàn phím gốc (SamsungKeypad) để tránh kẹt trạng thái
    dev.shell(['ime', 'set', 'com.sec.android.inputmethod/.SamsungKeypad'])
    ```
  - **Lưu ý quan trọng:** Tên Action Intent chính xác là `ADB_KEYBOARD_INPUT_TEXT` với extra string key là `text` (chứa chuỗi base64). Không dùng `ADB_INPUT_B64` hay `ADB_INPUT_TEXT` vì một số phiên bản AdbKeyboard cũ không bắt action này.

## 3. Quy Tắc Đối Với User & Anti-Paralysis
- Khi User yêu cầu viết bio bằng tiếng Việt: BẮT BUỘC viết đầy đủ dấu tiếng Việt chuẩn xác 100%, tuyệt đối không tự ý fallback về tiếng Việt không dấu rồi ngụy biện do giới hạn kỹ thuật.
- Khi nghiệm thu thứ tự video hoặc bio, bắt buộc soi thật WinRT OCR và tọa độ từng ô, không phát biểu bừa trước khi kiểm chứng.
