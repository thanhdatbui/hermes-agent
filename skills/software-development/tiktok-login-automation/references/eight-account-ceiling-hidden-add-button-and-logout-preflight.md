# Bẫy Chạm Trần 8 Nick Ẩn Nút Thêm Tài Khoản & Kỷ Luật Logout Trước Khi Login Mới (11/10/2026)

## 1. Cơ Chế UI TikTok Khi Chạm Trần 8 Tài Khoản
- TikTok trên Android quy định cứng tối đa 8 tài khoản đăng nhập đồng thời trên một thiết bị.
- Khi máy đã đủ 8 tài khoản (1 active profile + 7 nick trong bottom-sheet Switcher):
  * TikTok **ẨN HOÀN TOÀN** nút `Thêm tài khoản` (`Add account` / `Thêm tài khoản khác`).
  * Cuộn bottom-sheet Switcher lên kịch đáy cũng chỉ thấy danh sách 7 nick phụ, không có bất kỳ nút nào để vào màn hình Authentication Landing.
- **Hậu quả**:
  * Các script tự động đăng nhập (như `tiktok_login_v1.py`) cố tìm nút `Thêm tài khoản`, thử cuộn 3 lần và cuối cùng văng `UI_XML_TIMEOUT` hoặc `STOPPED: deadline-exceeded`.

## 2. Kỷ Luật Thứ Tự 3 Bước Bắt Buộc Khi Điều Phối Nick Dư
Khi một máy thừa nick cần đổi slot (ví dụ Máy 74 dồn 9 nick, chọn nick non nhất đẩy sang Máy 266 để đưa nick chính chủ `muyduyen4589` vào):
- **BƯỚC 1 — Bật 2FA & Lưu Pass Cho Nick Chuyển Đi (Trên máy nguồn)**:
  * Chạy Phase B tự động (`run_capture_phase_b.py --live`) trên máy nguồn.
  * Lấy Secret Key 32 ký tự, đặt mật khẩu farm chuẩn, ghi nhận vào workbook máy nhận.
- **BƯỚC 2 — ĐĂNG XUẤT NGAY KHỎI MÁY NGUỒN (OUT RA ĐỂ GIẢI PHÓNG SLOT)**:
  * CẤM nhảy cóc sang login nick đích ngay sau bước 1!
  * BẮT BUỘC thực hiện logout nick chuyển đi (Vào Profile nick đó -> Menu 3 gạch -> Cài đặt và quyền riêng tư -> Cuộn đáy -> Đăng xuất).
  * Chụp ảnh Switcher nghiệm thu: xác nhận máy nguồn chỉ còn 7 nick và nút `+ Thêm tài khoản` đã xuất hiện trở lại ở đáy bottom-sheet.
- **BƯỚC 3 — TIẾN HÀNH LOGIN NICK ĐÍCH**:
  * Chạy `tiktok_login_v1.py` để nạp nick chính chủ vào slot vừa giải phóng.

## 3. Cứu Hộ Stub UiAutomator Cho atx-agent (S7 / Android 7-8)
- Khi `run_capture_phase_b.py` hoặc ATX dump văng lỗi `non_xml_ui_dump` hoặc `UI_XML_TIMEOUT`:
  * Nguyên nhân: Gói stub `com.github.uiautomator` và `com.github.uiautomator.test` bị thiếu hoặc uninstalled ngầm trên máy.
  * Kho APK chuẩn có sẵn trên host:
    - `C:\Users\Kibe\.GemPhoneFarm\app\app-uiautomator.apk`
    - `C:\Users\Kibe\.GemPhoneFarm\app\app-uiautomator-test.apk`
  * Quy trình cứu hộ nhanh qua ADB:
    ```bash
    adb -s <serial> push "C:/Users/Kibe/.GemPhoneFarm/app/app-uiautomator.apk" /data/local/tmp/
    adb -s <serial> push "C:/Users/Kibe/.GemPhoneFarm/app/app-uiautomator-test.apk" /data/local/tmp/
    adb -s <serial> shell pm uninstall com.github.uiautomator
    adb -s <serial> shell pm uninstall com.github.uiautomator.test
    adb -s <serial> shell pm install -t -g /data/local/tmp/app-uiautomator.apk
    adb -s <serial> shell pm install -t -g /data/local/tmp/app-uiautomator-test.apk
    ```
    Sau khi cài đặt lại 2 stub APK, `atx-agent` sẽ dump XML bình thường trong < 1 giây.
