# Dual-Cluster Device Locks & Subprocess Stderr Unmasking (2026-10-19)

## 1. Subprocess Error Masking by Benign Stderr Lines

### Triệu chứng
Batch Alert báo lỗi kiểu:
```
UploadScriptError:UploadHook: [HOST] host=admin machines=200-999 workbook_root=D:\OneDrive\TaadaaData\admin runtime=D:\Taadaa\runtime\admin
```
Thực tế `[HOST] ...` là dòng cấu hình host info do `taadaa_host.host_guard()` in ra `sys.stderr` trên mọi tiến trình hợp lệ.

### Nguyên nhân
Hàm bóc tách lỗi con (`_extract_upload_subprocess_error`) đọc `stderr` trước `stdout` và lấy dòng cuối cùng (`lines[-1]`) mà không lọc các dòng benign:
- Dòng `[HOST]` (thông tin định tuyến host)
- Dòng `Warning:` / `WARNING:` (cảnh báo Python deprecation / SSH host key)
- Dòng OpenSSH crypto banner (`permanently added`, `post-quantum key exchange`)

Khi đó, lỗi thật sự nằm trong `stdout` (như `Workflow failed: [NEEDS_USER_DECISION] ACQUIRE_LOCKS...`) bị che giấu hoàn toàn.

### Quy tắc chuẩn hóa
1. Luôn lọc bỏ các dòng non-error khỏi `stderr` trước khi trích xuất:
   ```python
   err_lines = [
       l for l in lines
       if not l.startswith("[HOST]")
       and not l.lower().startswith("warning:")
       and "permanently added" not in l.lower()
   ]
   ```
2. Trong `stdout`, ưu tiên quét ngược tìm các pattern lỗi rõ ràng:
   `[error]`, `[critical]`, `workflow failed:`, `needs_user_decision`, `traceback`, `exception`.

---

## 2. Điểm mù Dual-Cluster Device Locks (Kibe vs Admin Farm)

### Triệu chứng
Hàng loạt máy cụm Admin (M201-280) đồng loạt thất bại ở bước hook upload với lỗi:
`[NEEDS_USER_DECISION] ACQUIRE_LOCKS: Cần user quyết định cho device lock` do lock cũ bị kẹt.

### Nguyên nhân gốc rễ
1. `reap-dead-owner-locks.py` và `watch_device_locks.py` mặc định dùng `Path.home() / ".codex" / "device-locks"`.
2. Khi cron chạy trên máy Kibe, `Path.home()` là `C:\Users\Kibe`, do đó script chỉ dọn dẹp các máy 1-80 cục bộ, hoàn toàn bỏ qua thư mục `C:\Users\Admin\.codex\device-locks\` trên máy Admin-PC (`192.168.110.119`).
3. Máy Admin-PC không có daemon Hermes chạy nền và không có scheduled task chạy reap định kỳ.
4. Khi một job trên Admin-PC (ví dụ: `tiktok-add-bao-mat-f2a`) thoát đột ngột mà không giải phóng lock, hàng chục lock mồ côi bị bỏ rơi vĩnh viễn trên đĩa Admin-PC.

### Giải pháp Dual-Cluster Reaper
Trong `reap-dead-owner-locks.py`:
- Sau khi quét sạch đĩa local (Kibe), nếu phát hiện đang ở host Kibe, tự động kích hoạt remote sweep trên Admin-PC qua `admin_ssh.py`:
  ```python
  if "admin" not in str(Path.home()).lower():
      admin_ssh_tool = Path(r"D:\Taadaa\tools\admin_ssh.py")
      if admin_ssh_tool.exists():
          subprocess.run([
              sys.executable,
              str(admin_ssh_tool),
              "--powershell",
              "python 'D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py'"
          ], timeout=30)
  ```
- Trên máy Admin-PC, khi script chạy sẽ phát hiện `Path.home()` chứa "admin" và chỉ dọn local `C:\Users\Admin`, tránh đệ quy vòng lặp.
- Đảm bảo toàn bộ 2 cụm (M1-80 và M201-280) đều được quét dọn sạch sẽ trong mỗi chu kỳ cron 5 phút.
