# Device Lock & Hermes Subshell Pitfalls for Canary Runs

## 1. Xử lý Stale Device Lock (Machine Lock)
- **Vấn đề**: Khi chạy canary cho máy `N`, script báo lỗi:
  `device lock active: path=C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json pid=<PID>`
- **Nguyên nhân**:
  - PID đó thường là tiến trình batch multi-machine trước đó (`multi-machine-feed-session --machines 1..80`).
  - Batch runner giữ reservation lock cho tất cả máy trong danh sách cho đến khi toàn bộ batch kết thúc.
  - Tuy nhiên, máy `N` có thể đã hoàn thành hoặc kết thúc sớm hơn các máy còn lại (kiểm tra `summary.txt` trong thư mục artifact của máy `N`).
- **Cách xử lý an toàn**:
  1. Kiểm tra PID bằng `Get-Process -Id <PID>`.
  2. Nếu PID đã chết, hoặc kiểm tra thấy máy `N` đã kết thúc trong artifact batch (`reason: "feed-session-smoke completed"` hoặc dừng hẳn), lock này là stale reservation lock.
  3. Xóa file lock: `Remove-Item 'C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json' -Force`.

## 2. Hermes Subshell `$env:PYTHONPATH` Poisoning (PIL `_imaging` ImportError)
- **Vấn đề**: Khi gọi PowerShell chạy `run-feed-session.ps1` hoặc `run_tiktok.py` từ Hermes Agent, gặp lỗi:
  `ImportError: cannot import name '_imaging' from 'PIL' (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)`
- **Nguyên nhân**:
  - Runtime của Hermes Agent tự động inject `$env:PYTHONPATH` trỏ vào venv nội bộ của Hermes (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\...`).
  - Khi script PowerShell gọi `python`, tiến trình Python con bị ép đọc site-packages của Hermes venv thay vì môi trường Python chuẩn của hệ thống / automation env, làm xung đột các C-extension compiled như PIL `_imaging`.
- **Giải pháp bắt buộc**:
  Luôn cô lập và xóa `$env:PYTHONPATH` trong lệnh thực thi PowerShell:
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -Command '$env:PYTHONPATH = ""; & "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row <R> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run'
  ```

## 3. Phân biệt `queued_v2` Lock vs Stale Lock & Cảnh báo `owner_process_alive`
- **Phân biệt `queued_v2` Lock**:
  - Khi multi-machine batch khởi chạy (`--mode multi-machine-feed-session`), nó pre-lock tất cả các máy với `status: "queued_v2"`, `lock_protocol_version: 2`.
  - Nếu PID batch runner còn sống (`Get-Process -Id <PID>`) và máy `N` chưa có thư mục con trong `.../machines/machine_<N>`, máy này **chưa chạy xong mà đang chờ trong hàng đợi worker**.
  - **CẤM XÓA LOCK** khi status là `queued_v2` và PID batch đang sống: Xóa lock sẽ gây tranh chấp tài nguyên nghiêm trọng khi worker batch đến lượt máy `N`. Chỉ canary khi batch PID đã dừng hoặc máy `N` đã hoàn thành.
- **Contract `owner_process_alive` trong `automation-core`**:
  - Hàm `automation_core.device_lock.owner_process_alive(owner)` nhận vào **dictionary** (ví dụ `{"pid": 243220}` hoặc dict parse từ JSON lock), **KHÔNG** nhận `int`.
  - Truyền `owner_process_alive(243220)` sẽ gây `AttributeError: 'int' object has no attribute 'get'`.
  - Đúng chuẩn: `owner_process_alive({"pid": <PID>})`.

## 4. Cấm `grep -rn` quét rộng codebase (Tránh 900s timeout)
- Không bao giờ dùng `grep -rn` hoặc quét đĩa diện rộng trên thư mục `python_runner` hay repo root: có cache, venv, log dung lượng lớn gây timeout 900s và cạn turn của Agent.
- Luôn dùng `inspect_machine.py <N>`, kiểm tra file log cụ thể hoặc dùng `search_files` có giới hạn `file_glob`.
