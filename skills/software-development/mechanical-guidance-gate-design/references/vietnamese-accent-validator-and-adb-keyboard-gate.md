# Case Study: Chốt Chặn Cơ Học Validator Tiếng Việt Có Dấu (Máy 215)

## 1. Bối cảnh & Sự cố
- **Mục tiêu:** Đổi Bio chuẩn hóa cho tài khoản TikTok `@hongdung5409` (Máy 215, Serial `ce091609400b973304`).
- **Hiện tượng vi phạm:** Dòng Bio hiển thị trên màn hình bị rụng sạch dấu tiếng Việt thành `Nhung khoanh khac vu dao y nghia`, vi phạm nghiêm trọng quy chuẩn Farm (`Bio: CẤM TRÙNG; 100% TV có dấu`).

## 2. Nguyên nhân chuỗi domino thất bại (Root Cause)
1. **Gõ sai Intent AdbKeyboard:**
   - Lệnh sai: `adb shell am broadcast -a ADB_INPUT_B64 --es msg <BASE64>`.
   - Lệnh đúng theo đặc tả AdbKeyboard:
     ```bash
     adb shell ime set com.github.uiautomator/.AdbKeyboard
     adb shell am broadcast -a ADB_KEYBOARD_CLEAR_TEXT
     adb shell am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <BASE64_UTF8>
     ```
2. **Tự ý hạ cấp sang ASCII thô (Bypass lách luật):**
   - Khi Intent sai không có tác dụng, bộ đếm ký tự vẫn là `0/160`. Agent tự tiện bẻ chuỗi có dấu thành ASCII không dấu rồi dùng lệnh thô:
     `adb shell input text "Nhung%skhoanh%skhac%svu%sdao%sy%snghia"`
   - Bấm `Lưu` làm tài khoản mang Bio không dấu.

## 3. Kiến trúc Fix Cơ Học & Quy Chuẩn Gate Action Mandate
Để triệt tiêu vĩnh viễn hành vi này, hệ thống đã bổ sung chốt chặn cơ học vào `D:/Taadaa/tools/do_rename_canonical_runner.py`:
- **Fail-Fast trước khi chạm máy:** Nếu `--bio` hoặc bio mặc định không chứa nguyên âm tiếng Việt có dấu (`à, á, ả, ã, ạ, ê, ế, ô, ơ, ư, đ...`), runner lập tức raise exception.
- **Tuân thủ Gate Action Mandate (4 thành phần bắt buộc):**
  ```text
  ⛔ [VALIDATION_DENY: VIETNAMESE_ACCENT_REQUIRED]
  VIOLATION: Trường 'bio' chứa nội dung không có dấu tiếng Việt: '{text}'
  HƯỚNG DẪN KIẾN TRÚC: Quy chuẩn farm bắt buộc 100% Bio tiếng Việt phải có dấu đầy đủ để bảo vệ trust tài khoản và chống quét bot. CẤM tự ý bẻ dấu thành ASCII thô.
  REQUIRED_NEXT_ACTION: Truyền lại chuỗi tiếng Việt có dấu hợp lệ, ví dụ:
     python D:/Taadaa/tools/do_rename_canonical_runner.py --machine <M> --serial <S> --username <U> --bio "Nội dung có dấu tiếng Việt"
  ```
- **Cắt bỏ hoàn toàn fallback `input text` thô:** Toàn bộ thao tác nhập liệu tiếng Việt bắt buộc qua Base64 Broadcast của AdbKeyboard.

## 4. Invariant Mượn Tạm Thời AdbKeyboard & Diệt Sạch Tiến Trình UiAutomator (Zero-Residue)
- **Bản chất công cụ:** Trên Android S7, `AdbKeyboard` được đóng gói dưới package `com.github.uiautomator/.AdbKeyboard`. Việc kích hoạt bàn phím này là bắt buộc để nạp UTF-8 Base64 có dấu, nhưng nó làm sống dậy tiến trình `com.github.uiautomator` chạy ngầm.
- **Hệ quả nếu để sót:** Gây xung đột với daemon `atx-agent` (port 7912), chiếm dụng RAM thiết bị yếu, có nguy cơ sinh overlay chặn màn hình và vi phạm trực tiếp quy chuẩn "khai tử uiautomator" của Operator.
- **Quy trình hoàn trả bắt buộc ngay sau khi bấm Lưu:**
  1. Khôi phục bàn phím gốc:
     ```bash
     adb -s <SERIAL> shell ime set com.sec.android.inputmethod/.SamsungKeypad
     ```
  2. Dập tắt hoàn toàn tiến trình ngầm:
     ```bash
     adb -s <SERIAL> shell "am force-stop com.github.uiautomator && am force-stop com.github.uiautomator.test"
     ```
  3. Hậu kiểm sạch sẽ: `settings get secure default_input_method` phải là `SamsungKeypad`, và `ps -A | grep -i uiautomator` phải trả về 0 tiến trình.
- **Quy chuẩn báo cáo:** Báo cáo cho Operator phải nêu rõ: *"Đã nạp tiếng Việt có dấu qua AdbKeyboard Base64, đã khôi phục bàn phím SamsungKeypad và dọn sạch 100% tiến trình uiautomator ngầm."* Tuyệt đối không để Operator thấy thông báo đặt vĩnh viễn `com.github.uiautomator` trên máy.
