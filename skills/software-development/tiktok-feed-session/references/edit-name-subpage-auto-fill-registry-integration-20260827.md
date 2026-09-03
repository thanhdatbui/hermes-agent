# Tích hợp tự động điền tên hiển thị tiếng Việt & Xử lý màn hình Edit Name Subpage trong benign_popup_registry

## 1. Hiện tượng & Triệu chứng
- **Alert Telegram / Error log:** `🚨 [MÁY X] DỪNG PHIÊN • Script: multi-machine-feed-session • Lý do: unknown TikTok state • Trạng thái: GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`
- **Màn hình thực tế:** Máy đang mở màn hình con chỉnh sửa tên TikTok:
  - Nút `Hủy` ở góc trên bên trái `[24,72][161,204]`.
  - Nút `Lưu` ở góc trên bên phải `[925,72][1056,204]` (ban đầu mờ do chưa nhập text).
  - Tiêu đề `Tên` / `Name`.
  - Ghi chú: `Bạn chỉ có thể đổi tên một lần mỗi 7 ngày.`
  - Trường nhập: EditText với placeholder `Thêm tên bạn mong muốn` (bounds `[48,504][1032,648]`, rid `hjp` hoặc `hnq`).

## 2. Nguyên nhân gốc (Root Cause)
- Khi tài khoản chưa có Display Name (mới reg hoặc chưa đặt tên), trang Profile hiển thị nút `"Thêm tên"` thay vì tên hiển thị.
- Khi flow preflight / navigate Profile chạm vào vùng header hoặc click vào action "Thêm tên", TikTok chuyển hướng vào màn hình con sửa tên (`SplashActivity`).
- Ở màn hình con này, không có các tab bottom bar (`Trang chủ`, `Bạn bè`, `Hồ sơ`, v.v.) và không có header switcher.
- `classifier.py` không có rule cho màn hình này nên rơi xuống `unknown` -> `safety_check` ném `SAFETY_MANUAL_NEEDED` với `unknown TikTok state` và dừng phiên.

## 3. Kiến trúc xử lý tự động trong `tiktok-luot nuoi acc`

### A. Nhận diện màn hình trong `core/benign_popup.py` & `core/classifier.py`
- `detect_edit_name_subpage(root)`: Quét XML tìm các marker:
  - Text/hint: `"thêm tên bạn mong muốn"` / `"them ten ban mong muon"`.
  - Ghi chú 7 ngày: `"chỉ có thể đổi tên một lần mỗi 7 ngày"` / `"bạn chỉ có thể đổi tên"`.
  - Nút `Hủy` / `Lưu`.
- `classify_tiktok_screen(root)`: Phân loại màn hình này về `GENERIC_POPUP_SCREEN` (`manual-needed:popup`) với reason `"profile edit name subpage detected"`.

### B. Đăng ký Handler trong `flows/benign_popup_registry.py`
- Đăng ký `edit_name_subpage_overlay` với priority **84** (chạy trước popup gợi ý bạn bè và sau location prompt).
- **Detector:** `_detect_edit_name(xml_content, ocr_text)` kiểm tra chuỗi `thêm tên bạn mong muốn` hoặc `chỉ có thể đổi tên`.
- **Dismisser:** `_dismiss_edit_name(ctx)`:
  1. Lấy thông tin tài khoản/email: `ctx.config.get("_account_email")` hoặc `ctx.account`.
  2. Tạo tên tiếng Việt chuẩn: `make_tiktok_name(email)` (phân bổ ngẫu nhiên theo Họ + Đệm + Tên, Họ + Tên, Đệm + Tên, Tên + Biệt danh đời thường, hoặc Duo dễ thương).
  3. Tap focus vào ô EditText `(540, 576)`.
  4. Chuyển bàn phím sang AdbKeyboard: `adb shell ime set com.github.uiautomator/.AdbKeyboard`.
  5. Xóa text cũ và broadcast text tiếng Việt dạng Base64 an toàn: `am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <base64>`.
  6. Ẩn bàn phím (`KEYCODE_ESCAPE`), tap nút `Lưu` `(990, 138)`.
  7. Bắt dialog xác nhận 7 ngày -> tap `Xác nhận` `(750, 1175)` / `(541, 1104)`.
  8. Trả lại bàn phím mặc định của thiết bị: `adb shell ime set com.sec.android.inputmethod/.SamsungKeypad`.
  9. Fallback an toàn: Nếu việc điền tên gặp lỗi, tự động tap nút `Hủy` `(90, 138)` để đưa máy trở lại màn hình Profile root an toàn.

## 4. Quy trình xử lý sự cố Live (Rescue Machine)
1. Kiểm tra trạng thái máy qua ATX XML dump (port 7912) và chụp screencap.
2. Thực hiện các bước nhập tên qua AdbKeyboard + Base64 như quy trình trên.
3. Verify lại XML để đảm bảo Profile đã xuất hiện Display Name và sticky header `com.ss.android.ugc.trill:id/pcq`.
4. Xóa file lock tương ứng trong `~/.codex/device-locks/` (`machine_X.lock.json` và `serial_*.lock.json`) để giải phóng máy.
