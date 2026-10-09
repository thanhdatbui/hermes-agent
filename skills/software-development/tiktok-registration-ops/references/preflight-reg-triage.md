# Preflight Reg Bù Triage & O(1) Inspection Rules

## 1. Tránh nghẽn I/O (NTFS Timeout > 180s)
- **Hiện tượng:** Thư mục `D:/Taadaa/Tiktok_Reg/screenshots_social/` chứa hàng chục nghìn file ảnh, và file `social_reg_log.txt` thường có dung lượng > 200MB.
- **Quy tắc cấm:**
  - CẤM dùng `ls -lt`, `find`, hoặc `search_files` quét thư mục `screenshots_social/` (sẽ gây timeout 180s treo phiên).
  - CẤM mở đọc file log bằng `f.readlines()` hay nạp toàn bộ vào bộ nhớ.
- **Kỹ thuật đọc log O(1) cuối file:**
  ```python
  import os
  path = 'D:/Taadaa/Tiktok_Reg/social_reg_log.txt'
  size = os.path.getsize(path)
  with open(path, 'rb') as f:
      f.seek(max(0, size - 4096))
      tail_content = f.read().decode('utf-8', errors='ignore')
      print(tail_content)
  ```

## 2. Bắt bệnh 4 nhóm lỗi Preflight Reg bù Row
Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` để kiểm tra trạng thái màn hình và focus:

1. **Nhóm UsbDebuggingActivity / ADB Timeout (`[01_open] not foreground` / `[adb-timeout]`):**
   - Focus: `com.android.systemui/com.android.systemui.usb.UsbDebuggingActivity`.
   - Nguyên nhân: Hộp thoại *"Allow USB debugging?"* hiện lên che kín foreground (hoặc mất kết nối ADB tạm thời do cáp/hub).
   - Xử lý: Cần cấp quyền USB Debugging ("Always allow") hoặc kiểm tra dây cáp, không can thiệp code reg.

2. **Nhóm không tìm thấy nút "Thêm tài khoản" (`[04_add_account] Không tìm thấy: ('Thêm tài khoản'`):**
   - Focus: `LauncherActivity` hoặc `TikTok`.
   - Nguyên nhân: TikTok đã đạt trần tối đa **8 tài khoản** (Row 1–8). Giao diện Switcher tự động ẩn nút "Thêm tài khoản".
   - Xử lý: Xác nhận số lượng tài khoản trên máy, loại máy này khỏi danh sách reg bù Row, chuyển target sang máy khác còn slot trống.

3. **Nhóm TikTok không foreground sau Clean Launch (`[01_open] TikTok not foreground`):**
   - Focus: `LauncherActivity`.
   - Nguyên nhân: Máy S7 bị đơ/chậm, ANR ngầm, hoặc app TikTok crash khi khởi chạy clean launch.
   - Xử lý: Clear cache TikTok package, kiểm tra tải RAM/bộ nhớ trước khi retry đơn lẻ.

4. **Nhóm Timeout chờ Login/Reg Success (`Timeout cho login`):**
   - Nguyên nhân: Kẹt ở bước chờ OTP Hotmail quá thời gian chờ (180s), hoặc vướng Captcha puzzle/xoay hình, hoặc màn hình khảo sát sở thích chặn luồng.
   - Xử lý: Kiểm tra hòm thư Hotmail (tình trạng lock/block), hoặc debug màn hình captcha.
