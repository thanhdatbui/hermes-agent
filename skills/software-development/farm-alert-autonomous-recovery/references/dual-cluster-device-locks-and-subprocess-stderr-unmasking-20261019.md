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
  home = str(Path.home()).replace("\\", "/").lower()
  host_id = os.environ.get("HOST_ID", "").strip().lower()
  machine_id = os.environ.get("MACHINE_ID", "").strip().lower()

  if "admin" in home or host_id.startswith("admin") or machine_id.startswith("admin"):
      return

  admin_ssh_tool = Path(r"D:\Taadaa\tools\admin_ssh.py")
  if not admin_ssh_tool.exists():
      return

  try:
      remote_script = "D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py"
      cmd = [
          sys.executable,
          str(admin_ssh_tool),
          "--powershell",
          f"python '{remote_script}'",
      ]
      res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
      if res.returncode == 0:
          for line in res.stdout.splitlines():
              if line.startswith("REAPED") or line.startswith("  m"):
                  print(f"[ADMIN-PC] {line}")
      else:
          print(f"[ADMIN-PC-WARN] reap exit={res.returncode}: {res.stderr.strip()[:100]}")
  except subprocess.TimeoutExpired:
      print("[ADMIN-PC-ERR] remote reap timed out after 30 seconds")
  except Exception as e:
      print(f"[ADMIN-PC-ERR] {e}")
  ```

---

## 3. Các cạm bẫy kỹ thuật (Pitfalls & Invariants)

1. **Cạm bẫy `sys.path.insert(0, site-packages)` gây shadowing namespace:**
   - Khi script chèn `sys.path.insert(0, r"D:\Taadaa\python-envs\automation\Lib\site-packages")`, thư mục `site-packages` chiếm ưu tiên cao nhất trong namespace Python.
   - Nếu trong `site-packages` có package tên `core` (từ thư viện ngoài), bất kỳ test hoặc code nào trong repo gọi `from core.account_config import ...` sẽ bị crash: `ModuleNotFoundError: No module named 'core.account_config'`.
   - **Quy tắc bắt buộc:** Luôn dùng `sys.path.append(...)` thay vì `sys.path.insert(0, ...)` khi nạp đường dẫn phụ của virtualenv ngoài repo.

2. **Quoting đường dẫn có khoảng trắng qua PowerShell SSH:**
   - Đường dẫn như `D:\Taadaa\tiktok-luot nuoi acc\...` có khoảng trắng. Khi gọi qua `admin_ssh.py --powershell`, bắt buộc bọc trong nháy đơn `f"python '{remote_script}'"`.
   - Lệnh PowerShell sẽ giải mã Base64 và thực thi chính xác chuỗi có nháy đơn mà không bị vỡ argument.

3. **Heuristic nhận diện Host chống vòng lặp vô tận (Infinite Loop Prevention):**
   - Không chỉ dựa vào `Path.home()`, kết hợp thêm `HOST_ID` và `MACHINE_ID` từ môi trường để xác định chính xác máy Admin-PC, bảo đảm không gọi đệ quy SSH về chính nó hoặc bị bypass khi cấu hình profile người dùng thay đổi.

4. **Bộ test suite bắt buộc khi triển khai remote wrapper:**
   - Test bỏ qua khi đang ở Admin host (`monkeypatch.setattr(Path, "home", ...)`).
   - Test bỏ qua an toàn khi tool SSH không tồn tại trên đĩa.
   - Test chuyển tiếp stdout `[ADMIN-PC]` khi `returncode == 0` kèm telemetry `duration_s`.
   - Test xử lý gracefully khi SSH trả về `returncode != 0`.
   - Test bắt ngoại lệ timeout (`subprocess.TimeoutExpired`) và lỗi mạng generic mà không làm crash tiến trình reaper chính.
   - Test tích hợp lock thật: dead owner -> quarantine, live owner -> kept, out of range -> untouched.
