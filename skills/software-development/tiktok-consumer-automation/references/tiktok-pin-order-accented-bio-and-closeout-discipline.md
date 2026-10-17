# TikTok Profile Automation: Video Pinning Order, Accented Bio & Closeout Discipline

## 1. Cơ chế Ghim Video TikTok (LIFO Order Invariant)
- **Thực tế hiển thị trên profile TikTok (Android):** TikTok áp dụng cơ chế LIFO (Last-In First-Out) cho hàng video ghim.
- **Thứ tự cột:**
  - Video ghim sau cùng sẽ chiếm vị trí **Cột 1 (Ngoài cùng bên trái - Vị trí số 1)**, đẩy các video đã ghim trước đó sang phải.
  - Vị trí thị giác ưu tiên cao nhất cho người xem là Cột 1 (Top-Left, theo F-pattern).
- **Quy trình đưa video Top View lên đầu tiên:**
  - Nếu video view cao nhất đang nằm ở Cột 2 hoặc Cột 3:
    1. Nhả ghim (Unpin) video đó.
    2. Chờ UI cập nhật (1-2s).
    3. Ghim lại (Pin) chính video đó.
    4. Video sẽ lập tức nhảy lên vị trí Cột 1 (ngoài cùng bên trái).

## 2. Gõ Tiếng Việt Có Dấu Trên Thiết Bị Android Farm (AdbKeyboard UTF-8 Invariant)
- **Vấn đề:** Lệnh `adb shell input text` chỉ hỗ trợ ASCII. Ký tự tiếng Việt có dấu (`à, á, ơ, ư, ô, ệ, ...`) sẽ bị drop, mất ký tự hoặc lỗi shell.
- **Giải pháp chuẩn:** Sử dụng IME `com.github.uiautomator/.AdbKeyboard` kết hợp broadcast Base64:
  ```python
  import base64
  # 1. Bật và gán bàn phím AdbKeyboard
  dev.shell(['ime', 'enable', 'com.github.uiautomator/.AdbKeyboard'])
  dev.shell(['ime', 'set', 'com.github.uiautomator/.AdbKeyboard'])
  
  # 2. Focus EditText và xóa sạch ký tự cũ
  # Lưu ý: Xóa sạch bằng Ctrl+A (meta 113, key 29) + Backspace (67) hoặc chuỗi backspaces
  
  # 3. Broadcast văn bản tiếng Việt có dấu qua Base64
  text = 'Học sinh ngoan nhưng hơi bất ổn - Follow tui nha!'
  b64 = base64.b64encode(text.encode('utf-8')).decode('ascii')
  dev.shell(['am', 'broadcast', '-a', 'ADB_KEYBOARD_INPUT_TEXT', '--es', 'text', b64])
  
  # 4. Trả lại bàn phím gốc sau khi nhập xong
  dev.shell(['ime', 'set', 'com.sec.android.inputmethod/.SamsungKeypad'])
  ```
- **Kỷ luật ngôn ngữ Bio:** Khi người dùng yêu cầu tiếng Việt, BẮT BUỘC gõ có dấu chuẩn 100%, cấm ngụy biện kỹ thuật để để tiếng Việt không dấu cẩu thả.

## 3. Kỷ Luật Khi Người Dùng Báo "Done" (Anti-Procedural Noise)
- Khi người dùng nói "Done", "Xong", "Wrap up", họ muốn chốt công việc hiện trường và nghỉ.
- **CẤM:** Lôi các diff commit cũ, lỗi gate nội bộ của module khác (ví dụ: `guard_cronjob_safety.py` chưa pass review) ra để "khóc lóc", giải trình dài dòng hoặc làm phiền người dùng.
- **HÀNH ĐỘNG ĐÚNG:**
  1. Kiểm tra hiện trường thiết bị (nhả lock, tắt màn hình/về launcher an toàn).
  2. Báo cáo súc tích 3-4 gạch đầu dòng về kết quả thực tế đạt được.
  3. Kết thúc phiên gọn gàng, không lải nhải thủ tục.
