# Vietnamese Accented Text via AdbKeyboard & TikTok Profile Optimization

## 1. Rule & User Preference: Bio & Text Input MUST Have Full Vietnamese Diacritics (Có Dấu Chuẩn)
- **CẤM TUYỆT ĐỐI gõ không dấu (ASCII-only):** Khi user yêu cầu viết Bio, đổi tên, hoặc comment tiếng Việt, BẮT BUỘC phải gõ tiếng Việt có dấu đầy đủ và chuẩn Unicode (NFC), tuyệt đối không tự ý fallback về text không dấu qua `adb shell input text`.
- Lệnh `adb shell input text` chỉ hỗ trợ ASCII và sẽ làm rụng hoặc vỡ toàn bộ ký tự có dấu.

## 2. Chuẩn Thao Tác Gõ Tiếng Việt Chuẩn Qua AdbKeyboard
Sử dụng IME `com.github.uiautomator/.AdbKeyboard` kết hợp broadcast Base64:

```python
import base64
import time

def input_vietnamese_accented_text(dev, text: str, focus_tap: tuple[int, int] | None = None):
    # 1. Kích hoạt và chọn IME AdbKeyboard
    dev.shell(["ime", "enable", "com.github.uiautomator/.AdbKeyboard"])
    dev.shell(["ime", "set", "com.github.uiautomator/.AdbKeyboard"])
    time.sleep(0.5)

    # 2. Focus vào ô nhập liệu nếu có tọa độ
    if focus_tap:
        dev.shell(["input", "tap", str(focus_tap[0]), str(focus_tap[1])])
        time.sleep(0.5)

    # 3. Xóa text cũ an toàn
    dev.shell(["am", "broadcast", "-a", "ADB_KEYBOARD_CLEAR_TEXT"])
    time.sleep(0.3)
    # Gửi thêm phím backspace phụ trợ phòng trường hợp intent không clear hết
    dev.shell(["input", "keyevent"] + ["67"] * 15)
    time.sleep(0.3)

    # 4. Encode UTF-8 sang Base64 ASCII và broadcast
    b64_msg = base64.b64encode(text.encode("utf-8")).decode("ascii")
    dev.shell(["am", "broadcast", "-a", "ADB_KEYBOARD_INPUT_TEXT", "--es", "text", b64_msg])
    time.sleep(1.0)
```

## 3. TikTok Profile: Cơ Chế Ghim Video (LIFO Pin Re-order)
- **Cơ chế LIFO:** Video được ghim sau cùng (last-in) sẽ được TikTok đẩy lên đứng ở **Vị trí số 1 ngoài cùng bên trái (Cột 1, Hàng 1)**.
- **Tình huống video top view bị kẹt ở Cột 2 hoặc Cột 3:**
  1. Nếu kênh đã ghim 3 video (hoặc video top view đang ở cột 2/3): Gọi hành động `UNPIN` (bỏ ghim) video top view đó trước.
  2. Ngay sau đó, gọi hành động `PIN` (ghim lại) video top view đó.
  3. TikTok sẽ lập tức đẩy video đó lên Vị trí số 1 đập ngay vào mắt người xem (F-pattern), tối ưu social proof cho profile.

## 4. Pitfall: Chụp Màn Hình Bị Đen / Trống (Screencap ~12KB Khi Screen Dozing)
- **Triệu chứng:** `screencap -p` tạo file ảnh chỉ ~12KB, WinRT OCR không đọc được text nào hoặc báo `handle_not_found`.
- **Nguyên nhân:** Thiết bị Samsung S7 rơi vào trạng thái ngủ / dozing (`Màn hình: OFF`), buffer đồ họa không render frame mới.
- **Xử lý:**
  1. Luôn kiểm tra và đánh thức máy: `input keyevent 224` (WAKEUP) và `input keyevent 82` (MENU/UNLOCK).
  2. Đảm bảo Activity cần chụp đã ở foreground (`dumpsys window windows | grep mCurrentFocus`).
  3. Chờ tối thiểu 1.5 - 2.0 giây cho activity vẽ xong frame trước khi chạy `screencap -p`.
