# Google Drive Taskbar Suppression & Remote Headless Mount Protocol (2026-10-20)

## Problem Summary
Khi Google Drive (DriveFS / Google Drive for Desktop) được cài đặt trên Windows (đặc biệt là máy farm hoặc máy tính vận hành từ xa như Admin-PC):
1. **Taskbar Popups & Webview2 Onboarding:** Sau mỗi lần khởi động lại máy, Google Drive chưa nạp profile hoặc vừa update sẽ kích hoạt `WindowsNativeWindow` bật cửa sổ Onboarding / Promo lên Taskbar người dùng, chen ngang màn hình chơi game hoặc ứng dụng chính.
2. **Auto-Mount vs Headless Backup Conflict:** Nếu tắt hẳn mục khởi động của Google Drive trong Windows Startup (`HKCU\...\Run`), ổ `G:\` sẽ không tự mount khi máy khởi động lại, khiến các tác vụ cron backup tự động (như `sync_and_clean_gdrive.py`) thất bại vì thiếu ổ đĩa đích.

---

## Technical Solution & Policies

### 1. Windows Registry Policies Triệt Tiêu Cửa Sổ Taskbar
Đặt các khóa Policy trong Registry (thử `HKCU\Software\Policies\Google\DriveFS`, nếu gặp PermissionError do siết quyền hệ thống thì fallback về `HKCU\Software\Google\DriveFS`):
* `DisableOnboardingDialog` (DWORD = 1): Ngăn chặn vĩnh viễn cửa sổ chào mừng/onboarding bung lên khi đăng nhập.
* `DoNotShowDialogs` (DWORD = 1): Chặn toàn bộ dialog nổi lên Taskbar.
* `AutoStartOnLogin` (DWORD = 0): Cấm Google Drive tự ý đăng ký lại mục khởi động của Windows.

### 2. Vô Hiệu Hóa Startup Run Key An Toàn
* Khóa: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
* Quy tắc: Không xóa mù mà đổi tên `GoogleDriveFS` thành `__disabled_GoogleDriveFS` để lưu lại đường dẫn gốc và cờ `--startup_mode`.

### 3. Tự Động Kích Hoạt Ngầm Khi Cần Sao Lưu (On-Demand Headless Mount)
Trong script cron sao lưu (ví dụ `sync_and_clean_gdrive.py`):
```python
def ensure_gdrive_mounted():
    if GDRIVE_ROOT.parent.is_dir():
        return True
    
    # 1. Tìm executable (ưu tiên đường dẫn cố định, fallback tìm thư mục version mới nhất)
    exe = r'C:\Program Files\Google\Drive File Stream\132.0.0.0\GoogleDriveFS.exe'
    if not os.path.exists(exe):
        base_dir = r'C:\Program Files\Google\Drive File Stream'
        if os.path.isdir(base_dir):
            versions = sorted(
                [d for d in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, d, 'GoogleDriveFS.exe'))]
            )
            if versions:
                exe = os.path.join(base_dir, versions[-1], 'GoogleDriveFS.exe')

    # 2. Chạy ngầm với CREATE_NO_WINDOW
    if os.path.exists(exe):
        flags = 0x08000000 if sys.platform == 'win32' else 0
        subprocess.Popen([exe, '--startup_mode'], creationflags=flags)
        
        # 3. Đợi mount tối đa 15 giây
        import time
        for _ in range(15):
            time.sleep(1)
            if GDRIVE_ROOT.parent.is_dir():
                return True
    return False
```
* Đặt lệnh guard `if not ensure_gdrive_mounted(): return False` ngay đầu hàm sync trước khi chạm vào bất kỳ đường dẫn `GDRIVE_ROOT` nào.

---

## Cạm Bẫy Thực Thi & Triển Khai Từ Xa Qua SSH

1. **Bẫy Windows cmd.exe 8191 Character Limit:**
   * Khi truyền payload Python dạng `python -c "exec(base64.b64decode(...))"` qua SSH sang Windows, script AST/payload dài (> 8KB) sẽ bị Windows cmd.exe từ chối với lỗi: `The command line is too long`.
   * **Giải pháp:** Sử dụng nén `zlib`:
     `compressed = zlib.compress(payload.encode('utf-8'))`
     `encoded = base64.b64encode(compressed).decode('ascii')`
     `cmd = 'python -c "import base64,zlib;exec(zlib.decompress(base64.b64decode(\'' + encoded + '\')).decode(\'utf-8\'))\" apply'`
     Giúp giảm kích thước payload từ ~9.6KB xuống ~2.9KB.

2. **Ghi File Nguyên Tử (Atomic File Write):**
   * Khi patch script nguồn trên máy từ xa hoặc local, không dùng `open(path, 'w')` trực tiếp. Phải ghi ra `path + '.tmp'`, sau đó gọi `os.replace(path + '.tmp', path)` để tránh hỏng file nếu tiến trình bị kill giữa chừng.
