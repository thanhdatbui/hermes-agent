# Xử Lý Pop-up USB Debugging & Nhận Diện Đủ 8 Acc Qua Resource-ID NDK (2026-09-21)

## 1. Bối cảnh Sự cố (Incident Preflight Reg Bù Row 7)
Trong đợt chạy Preflight Reg bù Row 7 ngày 21/09/2026, 13 máy gặp lỗi:
- Nhóm M27, M37: `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`
- Nhóm M20, M46, M63: `Timeout cho login`
- Nhóm M22, M48, M53, M55: Bị che foreground bởi UsbDebuggingActivity hoặc adb-timeout.

---

## 2. Nguyên nhân & Giải pháp Kỹ thuật

### A. Pop-up UsbDebuggingActivity gây Timeout Login (M20, M46, M63)
- **Cơ chế lỗi**:
  Ngay sau khi nhập OTP thành công và TikTok chuẩn bị load trang Home/Profile, hộp thoại hệ thống Android **"Cho phép gỡ lỗi USB?"** (`com.android.systemui/com.android.systemui.usb.UsbDebuggingActivity`) bất ngờ xuất hiện đè lên màn hình.
  Hàm `wait_login_success` kiểm tra `APP_PACKAGE not in (xml or "")` và thấy package là `com.android.systemui`, rơi vào nhánh chờ `non-TikTok and non-Outlook foreground... waiting` cho đến khi hết timeout 30s.
- **Handler tự động (`dismiss_usb_debugging_dialog`)**:
  Được thêm vào `social_reg_v1.py`:
  1. Kiểm tra XML có chứa `"cho phep go loi usb"` hoặc `"allow usb debugging"`.
  2. Tự động tick chọn checkbox *"Luôn cho phép từ máy tính này"* (*"Always allow from this computer"*).
  3. Nhấn nút *"OK"* (`android:id/button1`) để cấp quyền vĩnh viễn và đóng popup.
  4. Đã tích hợp vào `_dismiss_system_popups` và 2 vị trí trong vòng lặp `wait_login_success`.

### B. Nhận diện 8 Tài khoản bằng Resource-ID `ndk` (M27, M37)
- **Cơ chế lỗi**:
  TikTok trên máy M27 và M37 thực tế đã đăng nhập đủ 8 tài khoản (kịch trần tối đa của ứng dụng). Khi đủ 8 nick, menu Account Switcher tự động ẩn nút "Thêm tài khoản".
  Hàm `tap_add_account` có logic đếm số nick:
  ```python
  _acc_count = sum(1 for _n in _root.iter("node") if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]))
  ```
  Do TikTok app v30+ đổi mã obfuscated của text username sang `ndk`, danh sách cũ không khớp nên `_acc_count` bị tính = 0, khiến code rơi xuống ném `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)` thay vì ném `MACHINE_FULL_8_ACCOUNTS`.
- **Giải pháp**:
  Bổ sung `"ndk"` vào danh sách resource-id trong `tap_add_account`. Khi `_acc_count >= 8`, code tự log `Máy đã có {_acc_count} tài khoản — đạt giới hạn tối đa 8`, bấm Back đóng dropdown, về Home an toàn và ném `MACHINE_FULL_8_ACCOUNTS` để flow kết thúc chuẩn xác.
  Unit test: `tests/test_machine_full_8_acc.py` đã bổ sung test case và pass 100%.

### C. Invariant Bảo toàn Tài sản Farm: Cấm Ghi Đè Xóa Nick Cũ
- **Quy tắc tuyệt đối**: Mọi nick đã tồn tại trên farm là tài sản của user, CẤM xóa hoặc ghi đè kết quả reg mới vào các hàng slot đã có dữ liệu.
- Nick mới reg chỉ được điền vào hàng hoàn toàn trống (`ID is None and GMAIL is None`).
- Khi khôi phục: Nick cũ về đúng vị trí slot gốc ban đầu; nick mới reg đẩy xuống các slot trống phía dưới (Slot 7/8).
