# Launcher Pre-flight & Environment Isolation (run-feed-session.ps1)

## 1. Cô lập PYTHONPATH
Khi chạy `run-feed-session.ps1` hoặc các script launcher kích hoạt tiến trình Python:
- Luôn đảm bảo `$env:PYTHONPATH = ""` trước khi kích hoạt `python .\python_runner\run_tiktok.py` (hoặc đặt ở đầu script launcher).
- **Lý do**: Môi trường venv của host / Hermes Agent có thể xuất `PYTHONPATH` trỏ tới site-packages của host. Khi subprocess Python của repo chạy, nó sẽ ưu tiên nạp module từ `PYTHONPATH`, dẫn đến lỗi xung đột nhị phân C-extension (điển hình: `cannot import name '_imaging' from 'PIL'`).

## 2. Tự động kiểm tra & dọn dẹp Stale Device Lock
- **Đường dẫn lock**: `$env:USERPROFILE\.codex\device-locks\machine_${m}.lock.json`
- **Cơ chế hoạt động**:
  1. Đọc nội dung JSON từ file lock để lấy `pid` (`$lockData.pid`) và timestamp.
  2. Kiểm tra tiến trình bằng PowerShell:
     ```powershell
     $proc = if ($targetPid) { Get-Process -Id $targetPid -ErrorAction SilentlyContinue } else { $null }
     ```
  3. **Nếu tiến trình KHÔNG còn tồn tại** (stale lock sau sự cố/crash):
     - Tự động xóa file lock:
       ```powershell
       Remove-Item -Force -LiteralPath $lockPath -ErrorAction SilentlyContinue
       ```
     - Log thông báo: `[PRE-FLIGHT] Da xoa stale lock may $m (PID $targetPid da chet)`
  4. **Nếu tiến trình vẫn còn chạy nhưng lock > 600 giây**:
     - Ghi cảnh báo nghi ngờ tiến trình zombie:
       ```powershell
       Write-Warning "[PRE-FLIGHT] Canh bao: Lock may $m van con tien trinh PID $targetPid chay nhung da qua 600s ($([math]::Round($lockAgeSec))s). Kiem tra tien trinh zombie."
       ```

## 3. Pitfall cú pháp PowerShell quan trọng
- **CẤM** dùng `$pid` làm tên biến trong PowerShell (ví dụ: `$pid = $lockData.pid`).
- Trong PowerShell, `$PID` là biến read-only tự động của PowerShell engine lưu Process ID của chính tiến trình PowerShell đang chạy. Việc gán giá trị cho `$pid` sẽ throw exception runtime:
  `Cannot overwrite variable PID because it is read-only or constant.`
- **Khắc phục**: Luôn đặt tên biến rõ ràng như `$targetPid` hoặc `$lockPid`.
