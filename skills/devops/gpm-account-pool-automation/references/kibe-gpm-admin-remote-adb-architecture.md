# Kiến trúc On-Demand Remote ADB giữa Kibe (GPM Controller) và Admin (Phone Host)

## 1. Bối cảnh & Vấn đề
- **Mô hình Farm 2 máy:** Máy Kibe (quản lý GPM bản quyền, chạy OmniRoute OAuth) và máy Admin (IP LAN `192.168.110.119`, host dàn Samsung S7 reg Gmail, nuôi TikTok).
- **Vấn đề bản quyền & chi phí:** GPM chỉ có 1 key bản quyền trên máy Kibe. Khi Gmail mới reg từ máy Admin cần login lên GPM Kibe để lấy token OAuth, Google đòi xác minh 2FA / Google Prompt (chọn 2 số) / Security Code 10 số trên S7 cắm bên Admin.
- **Tại sao không chuyển 100% cron sang Kibe?**
  - Tránh Single Point of Failure: Kibe sập nguồn/update Windows thì dàn phone Admin vẫn tự reg, tự nuôi nick bình thường.
  - Device Watchdog: Các script chống treo, hạ nhiệt, tắt màn hình (`stayon=0`), reap app cần chạy local trên Admin để phản ứng O(1).
  - Tránh nghẽn mạng LAN/Tailscale khi dump video, XML liên tục.

## 2. Giải pháp On-Demand Remote ADB qua LAN/Tailscale
Thay vì Admin phải mua thêm antidetect hoặc Kibe ôm toàn bộ cron:
- **Admin giữ nguyên vai trò:** Vẫn chạy cron reg Gmail, feed TikTok, ghi nhận Excel độc lập.
- **Kibe đóng vai trò Trạm Xác thực & GPM tập trung:** Khi cần login profile GPM, Kibe chỉ bắn lệnh ADB qua LAN sang máy Admin đúng vài giây để lấy mã/tap prompt, sau đó trả máy cho Admin chạy tiếp.

## 3. Thiết lập trên máy Admin (Chạy 1 lần)
Mở Remote ADB Server lắng nghe trên mạng LAN (`0.0.0.0:5037`):
- File script đồng bộ tại: `D:\OneDrive\Taadaa_Sync_Shared\bat_remote_adb_admin.bat`
- Nội dung cốt lõi:
  ```cmd
  netsh advfirewall firewall add rule name="ADB Remote 5037" dir=in action=allow protocol=TCP localport=5037
  "%ADB_PATH%" kill-server
  "%ADB_PATH%" -a nodaemon server
  ```

## 4. Điều khiển từ xa từ máy Kibe
Tool thực thi chuẩn: `D:\Taadaa\tools\remote_admin_adb.py`
Hoặc gọi ADB qua cờ `-H`:
```bash
# Liệt kê thiết bị bên Admin
adb -H 192.168.110.119 devices

# Bấm phím Home máy S7 bên Admin
python tools/remote_admin_adb.py -s <serial> shell input keyevent 3

# Chụp ảnh màn hình kiểm tra Google Prompt
python tools/remote_admin_adb.py -s <serial> exec-out screencap -p > D:/Taadaa/tmp/prompt.png
```
