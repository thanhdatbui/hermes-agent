# Account Switcher Fast Inspection & Inventory Audit

## 1. Vị trí công cụ chuẩn trên Farm (Tránh dò tìm lãng phí Tool Calls)
- **ADB Binary**: Trên môi trường Windows farm, `adb` thường không nằm trong `PATH` mặc định của Git Bash/terminal. Đường dẫn binary chuẩn luôn nằm tại:
  - `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`
- **Device Locking & Multi-process Concurrency**:
  - `DeviceContext` nằm tại package: `automation_core.device_lock` (src: `D:\Taadaa\automation-core\src`), KHÔNG PHẢI `core.device` hay `automation_core.device`.
  - Signature chuẩn:
    ```python
    import sys
    sys.path.insert(0, r"D:\Taadaa\automation-core\src")
    from automation_core.device_lock import DeviceContext

    with DeviceContext(serial=serial, machine=machine_id, project="inspect_switcher", user_authorized=True):
        # Tương tác với thiết bị
    ```

## 2. Quy trình Inspect Account Switcher Nhanh
Để kiểm tra danh sách tài khoản TikTok thực tế trong Switcher mà không làm thay đổi trạng thái đăng nhập hoặc tốn quá nhiều lượt gọi lệnh:

1. **Wake & Unlock**:
   - `adb shell input keyevent 224` (WAKEUP)
   - `adb shell input keyevent 82` (MENU / Unlock)
2. **Mở TikTok vào thẳng Profile / Switcher**:
   - Mở TikTok: `adb shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1`
   - Chờ app load (~3-5s).
   - Tap tab Profile (thường ở góc dưới cùng bên phải: khoảng `x=960, y=1840` trên màn hình 1080x1920 hoặc qua resource id `com.ss.android.ugc.trill:id/profile_tab`).
   - Mở Account Switcher: Tap vào tên tài khoản / dropdown icon ở thanh header trên cùng (giữa màn hình hoặc phía trên profile name).
3. **Chụp ảnh hiện trường & Trích xuất UI XML**:
   - Chụp ảnh màn hình lưu vào `D:\Taadaa\reports\<machine>_switcher.png`:
     ```bash
     adb exec-out screencap -p > D:\Taadaa\reports\m1_switcher.png
     ```
   - Đọc danh sách nick:
     - Ưu tiên gọi atx-agent (nếu đang chạy trên port 7912): `http://127.0.0.1:<port>/dump/hierarchy`
     - Hoặc dump trực tiếp: `adb shell uiautomator dump /sdcard/switcher.xml && adb pull /sdcard/switcher.xml D:\Taadaa\reports\m1_switcher.xml`
     - Parse các `node` có thuộc tính `text` trong bottom sheet switcher (chứa username `@...` hoặc nickname).

## 3. Cạm bẫy sau khi Switch Account để Logout / Quản lý Nick: Popup "Follow bạn bè"
- **Hiện tượng**: Sau khi tap vào một tài khoản trong Account Switcher để switch sang nick đó (ví dụ để vào Cài đặt -> Đăng xuất nick ký sinh/lỗi), TikTok thường lập tức bung popup overlay modal:
  - Tiếng Việt: *"Follow bạn bè của bạn"* / *"Tìm bạn bè từ danh bạ"* / *"Lưu thông tin đăng nhập"*.
  - Tiếng Anh: *"Find friends"* / *"Sync contacts"*.
- **Hậu quả**: Overlay này che phủ toàn bộ màn hình Profile và thanh điều hướng dưới đáy. Nếu script ngay lập tức tap Menu 3 gạch (`x=1005, y=150`) hoặc Settings fallback, tap sẽ rơi vào vùng modal overlay hoặc không ăn, dẫn tới kẹt flow và timeout (180s).
- **Giải pháp xử lý bắt buộc**:
  1. Sau khi tap switch account, luôn chờ 2-3s và kiểm tra overlay trước khi thao tác tiếp.
  2. Dập overlay:
     - Kiểm tra nút đóng dialog (icon X, resource-id chứa `close` hoặc `btn_close`).
     - Hoặc gửi `adb shell input keyevent 4` (KEYCODE_BACK) 1 lần để dismiss overlay.
     - Tái sử dụng helper `dismiss_profile_overlays(device_id)` trong `social_reg_v1` để dọn sạch overlay trước khi tap Menu 3 gạch.
  3. Chỉ tap Menu 3 gạch khi đã xác nhận màn hình Profile hiển thị bình thường.

