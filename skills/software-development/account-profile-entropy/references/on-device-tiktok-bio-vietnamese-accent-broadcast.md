# On-Device TikTok Bio & Profile Text Update via Base64 UTF-8 Broadcast

## Bối Cảnh & Vấn Đề (User Correction 2026-10-17)
- **Vấn đề**: Khi Operator yêu cầu viết Bio hoặc mô tả hồ sơ bằng tiếng Việt ("Viết bio bằng tiếng Việt cho tao", "là sao đéo chịu gõ dấu cho tao v"), Agent có xu hướng gõ tiếng Việt không dấu qua `adb shell input text` vì cho rằng thiết bị Android 8 / Samsung S7 không hỗ trợ gõ có dấu qua ADB.
- **Hậu quả**: Khi gõ không dấu (`Hoc sinh ngoan nhung hoi bat on`), User bực bội và phản ánh gắt gao. Ngoài ra, việc dùng `adb shell input text` trực tiếp với văn bản dài hoặc có ký tự đặc biệt dễ làm vỡ shell buffer, rớt chữ, hoặc văng màn hình.
- **Kỹ thuật chuẩn xác**: Trên thiết bị Samsung S7 (Android 8) đã cài đặt sẵn `com.github.uiautomator/.AdbKeyboard`. Broadcast chuẩn xác hỗ trợ 100% tiếng Việt UTF-8 có dấu đầy đủ là:
  ```bash
  am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <BASE64_UTF8_STRING>
  ```

---

## 1. Cơ Chế Nhập Liệu Tiếng Việt Có Dấu Chuẩn Xác

### A. Phân Biệt Các Action Broadcast của AdbKeyboard
1. `ADB_INPUT_TEXT`: Chỉ nhận chuỗi ký tự raw, thường bị drop dấu thanh tiếng Việt trên Android 8.
2. `ADB_INPUT_B64`: Một số phiên bản AdbKeyboard cũ không bắt intent action này.
3. **`ADB_KEYBOARD_INPUT_TEXT` (Action chuẩn nhất trên Farm)**:
   - Nhận parameter `--es text <base64_string>`.
   - Giải mã Base64 sang chuỗi byte UTF-8 và commit trực tiếp vào `InputConnection` của EditText đang active.
   - Hỗ trợ đầy đủ tiếng Việt có dấu (`à, á, ả, ã, ạ, ô, ơ, ư, ê, đ...`), emoji và ký tự đặc biệt.

### B. Đoạn Code Python Chuẩn Mực
```python
import base64
import time

def type_vietnamese_accented_text(dev, text: str):
    """
    Nhập văn bản tiếng Việt có dấu 100% vào EditText đang focus trên Android S7.
    """
    # 1. Mã hóa văn bản sang Base64
    b64_text = base64.b64encode(text.encode("utf-8")).decode("ascii")

    # 2. Bật và chuyển IME sang AdbKeyboard
    dev.shell(["ime", "enable", "com.github.uiautomator/.AdbKeyboard"])
    dev.shell(["ime", "set", "com.github.uiautomator/.AdbKeyboard"])
    time.sleep(0.5)

    # 3. Gửi broadcast nạp text UTF-8
    dev.shell([
        "am", "broadcast",
        "-a", "ADB_KEYBOARD_INPUT_TEXT",
        "--es", "text", b64_text
    ])
    time.sleep(1.2)

    # 4. Trả bàn phím về SamsungKeypad mặc định của máy
    dev.shell(["ime", "set", "com.sec.android.inputmethod/.SamsungKeypad"])
    time.sleep(0.5)
```

---

## 2. Quy Trình Cập Nhật Bio TikTok Trên Farm (State Machine & Clear Trap)

### A. Bẫy Clear Text Trong Khung Nhập Bio (`ProfileEditActivity`)
- **Cạm bẫy**: Khi vào màn hình sửa Tiểu sử, khung `EditText` đã có sẵn nội dung cũ. Nếu chỉ bấm `Ctrl+A` (`keyevent --meta 113 29`) rồi xóa, một số trường hợp TikTok Android 8 không bôi đen toàn bộ mà chỉ đặt con trỏ ở giữa. Khi broadcast văn bản mới vào, chuỗi mới sẽ bị chèn lọt vào giữa chuỗi cũ, tạo ra văn bản rác hỗn tạp (VD: `Hoc sinh ngoan nHọc sinh ngoan...`).
- **Quy chuẩn Clear sạch 100%**:
  ```python
  # 1. Tap focus vào khung EditText
  dev.shell(["input", "tap", "500", "600"])
  time.sleep(0.4)

  # 2. Tap về cuối chuỗi và gửi lệnh di chuyển con trỏ về cuối (KEYCODE_MOVE_END = 123)
  dev.shell(["input", "tap", "950", "600"])
  dev.shell(["input", "keyevent", "123"])

  # 3. Gửi liên tiếp 60-80 keyevent DEL (67) theo batch
  dev.shell(["input", "keyevent"] + ["67"] * 80)
  time.sleep(0.5)
  ```

### B. Trình Tự Điều Hướng Vào Màn Sửa Tiểu Sử (Bio)
1. Từ màn hình Hồ sơ cá nhân (`PROFILE`), dòng Bio nằm ở `bounds=[36, 642][1044, 690]`. Chạm vào Bio hoặc nút "Sửa hồ sơ".
2. Vào màn hình `ProfileEditActivity`, tìm dòng **Tiểu sử** (nằm ở `y ≈ 1284 - 1500`, tap tại `(600, 1380)`).
3. Clear text theo mục (A) ở trên.
4. Nạp text tiếng Việt có dấu qua Base64 Broadcast theo mục (1.B).
5. Bấm nút **Lưu** ở góc trên cùng bên phải (`bounds=[925, 72][1056, 204]`, tap tại `(990, 138)`).
6. Nhấn phím Back (`keyevent 4`) để quay lại trang hồ sơ gốc và bấm tab Hồ sơ (`972, 1857`) để refresh cache giao diện.

---

## 3. Quy Tắc Visual Verification & Send-Gate
- **CẤM GỬI ẢNH MÙ**: Sau khi cập nhật Bio, BẮT BUỘC chụp ảnh màn hình và chạy thẩm định qua `media_verify.py` (`verify_media_target`).
- **Soi mắt kiểm tra trước khi gửi (`browser_vision`)**: Kiểm tra trực quan xem dòng Bio trên profile đã hiển thị tiếng Việt có dấu đầy đủ, chuẩn xác, không bị dính chữ hay lỗi font trước khi gửi báo cáo `MEDIA:<path>` cho User.
