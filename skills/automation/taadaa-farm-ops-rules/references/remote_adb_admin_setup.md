# Remote ADB Admin Setup & Auto-Start Rules

## 1. Kiến trúc kết nối Kibe -> Admin
- Máy Admin: `192.168.110.119:5037` (port ADB).
- Tool phía Kibe: `python D:/Taadaa/tools/remote_admin_adb.py` hoặc `adb -H 192.168.110.119 <args>`.
- File cài đặt chuẩn trên Admin: `D:\OneDrive\Taadaa_Sync_Shared\cai_dat_tu_dong_adb_admin.bat`.

## 2. Hard Invariant: CẤM Task Scheduler chạy quyền SYSTEM
- **Nguyên nhân lỗi Xiaowei / Popup RSA:** Khi chạy dưới `SYSTEM`, adb server dùng key tại `C:\Windows\System32\config\systemprofile\.android\adbkey`, lệch với key `C:\Users\Admin\.android\adbkey` của Xiaowei và dàn S7. Điều này khiến thiết bị nảy lại popup xin quyền hoặc Xiaowei mất kết nối thiết bị.
- **Quy chuẩn bắt buộc:**
  - Xóa bỏ triệt để mọi task `SYSTEM`: `Taadaa_ADB_Remote_Server`.
  - Chỉ đăng ký task chạy dưới quyền `User Admin` khi đăng nhập (`onlogon`): `Taadaa_ADB_User_Remote`.
  - Mở Firewall Inbound TCP port 5037 cho toàn bộ profile mạng LAN.
