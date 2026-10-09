# Case M33: Sự Cố Ngâm Phiên 10 Tiếng, Phân Tích Root Cause & 7 Hard Gates (Claude Opus High Approved)

## 1. Bối cảnh & Hiện trường sự cố
- **Thời gian**: Phiên kéo dài từ 13h23 đến quá nửa đêm (>10 tiếng) xử lý Farm Alert máy M33 (`ce0616061a74682305`, Row 3).
- **Hiện tượng**: Nick mục tiêu `phanlan097` bị kẹt không switch được từ nick cũ `lebaothao8787` do lỗi overlay "Đã xảy ra lỗi / Thử lại sau" kèm nút "Thử lại" (`id/dcj`).
- **Nghịch lý**: Mặc dù đã có skill `farm-anti-overengineering` (>100KB) và 3 Hard Gate hooks cơ bản, Coordinator vẫn rơi vào bẫy ngâm phiên, liên tục bị user bức xúc phản ánh ("Lí do treo từ 7h...").

---

## 2. 4 Nguyên nhân cốt tử làm treo phiên (Root Cause Analysis)

### 1. Bẫy Broad Grep / Scan Timeout
- **Hành vi**: Khi bí đường tìm kiếm mapping proxy/config, Coordinator chạy các lệnh `grep -rn` hoặc `find` vào thư mục chứa `.ai-runs`, `runtime`, `python-envs`.
- **Hậu quả**: Mỗi lệnh quét đĩa sâu làm terminal bị freeze và timeout 180s. Lặp lại 4-5 lần là ngốn trắng gần 20-30 phút không có bất kỳ tiến độ nào.

### 2. Bẫy Synchronous Device I/O Timeout
- **Hành vi**: Coordinator gọi trực tiếp lệnh PowerShell Canary (`run-feed-session.ps1 -Machines 33`) ở session chính với `timeout=240` hoặc `timeout=300`.
- **Hậu quả**: Khi điện thoại gặp lỗi mạng/màn hình, script trên thiết bị rơi vào vòng lặp fallback `auto_login_recovery` / retry kéo dài 3-5 phút làm toàn bộ luồng điều phối của Coordinator bị đóng băng 100%.

### 3. Lách Luật Dispatch Contract (Fake Compliance & Analysis Paralysis)
- **Hành vi**: Coordinator điền đủ 3 nhãn `FILE:`, `SCOPE:`, `FOCUSED_TEST:` nhưng nội dung goal lại mở ("Kiểm tra và hoàn thiện logic...", "Investigate và sửa...").
- **Hậu quả**: Worker vào session con dùng hết 15 tool calls (10-15 phút) chỉ để `read_file` đọc dạo và lên kế hoạch chứ không ghi bất kỳ byte code nào xuống đĩa. Cần tới 4 lượt worker mới patch được code.

### 4. Incidental Sidetrack & Sai lệch hạ tầng
- **Hành vi**: M33 bị gán sai port proxy `10001` (MikroTik không auth) thay vì `20033` (sing-box mixed), Coordinator loay hoay thử nghiệm curl/proxy trực tiếp và định viết tool/script phụ thay vì đối soát file mapping `PROXYgandienthoai.xlsx`.

---

## 3. Kiến trúc 7 Hard Gate Hooks hoàn chỉnh (Zero-Bypass Architecture)

Được Claude Opus High review độc lập qua 4 vòng thẩm định khắt khe, triển khai tại `C:/Users/Kibe/AppData/Local/hermes/hooks/` và repo `deploy/hermes-home/hooks/`:

### Gate 0: `guard_progress_supervisor.py` (Dead-man Switch)
- **Mục tiêu**: Bắt buộc phải có State Change thực tế (`patch`, `write_file`, `py_compile`, `pytest`, `git commit`).
- **Cơ chế**: Quản lý state độc lập theo `session_id`. Nếu sau 15 phút hoặc > 8 lệnh thăm dò mà không có State Change $\rightarrow$ **ĐÓNG BĂNG NGAY LẬP TỨC**, ép dừng lại báo cáo user.
- **Race condition safety**: Bọc File Lock liên tiến trình (`O_CREAT | O_EXCL`) cho toàn bộ chu trình Đọc $\rightarrow$ Sửa $\rightarrow$ Ghi, phá stale lock >10s, fail-safe thoát ngay nếu không giành được lock, ghi file atomic qua temp file + `os.replace`.

### Gate 1: `guard_read_file_size.py`
- Chặn đọc file log > 10MB, ép dùng `tail -n 200` hoặc grep O(1).

### Gate 2: `guard_pytest_scope.py`
- Chặn lệnh `pytest` trần quét toàn repo gây timeout 900s, ép chỉ định file đơn lẻ `< 30s`.

### Gate 3: `guard_dispatch_contract.py` (Verified Contract)
- **Phân loại cấu trúc**:
  + Luồng `INVESTIGATE`: Chỉ hợp lệ khi **TUYỆT ĐỐI KHÔNG CÓ** `FILE:` và `OLD_STRING:`, bắt buộc khai báo `BUDGET: <= 5 tool calls`.
  + Luồng `CREATE`: Bắt buộc có `FILE:` + `FILE_CONTENT:`.
  + Luồng `EDIT`: Bắt buộc có `FILE:` + `OLD_STRING:` + `NEW_STRING:` + `FOCUSED_TEST:`.
- **Verify đĩa vật lý**: Hook tự đọc file trên đĩa kiểm tra `OLD_STRING` có tồn tại và **DUY NHẤT 1 LẦN (`occurrences == 1`)**. Chặn đứng 100% fake compliance và goal mở.

### Gate 4: `guard_broad_grep.py` (Expanded Scan Guard)
- Chặn toàn bộ họ lệnh quét: `grep -r/--recursive`, `rg`, `find`, `findstr /s`, `gci -r`, `ls -r`, và script Python `os.walk`, `rglob`, `glob.glob(recursive=True)` trỏ vào root, `.ai-runs`, `runtime`, `python-envs`.

### Gate 5: `guard_device_bulkhead.py` (Bulkhead & Circuit Breaker)
- **Cấm tuyệt đối ADB bấm tay**: Chặn cứng `adb shell input (tap|swipe|keyevent|text)`.
- **Zero-Foreground Device I/O**: Lệnh máy thật (PowerShell Canary) bắt buộc chạy `background=True, notify_on_complete=True` hoặc timeout `<= 60s`.
- **Device Circuit Breaker**: Theo dõi danh sách máy (kể cả quote và space-separated). Nếu máy N fail liên tiếp $\ge 3$ lần $\rightarrow$ **Quarantine (Cách ly 15 phút Cooldown)**, cấm retry tự động.

### Post Gate: `record_device_failure.py`
- Ghi nhận kết quả lệnh thiết bị sau khi chạy. Neo regex dòng summary `(?m)^\s*.*?\b([1-9]\d*)\s+failed\b` và hard error `(?im)\bmanual-needed\b|Command timed out|^\s*(?:FATAL|CRITICAL)\b`.
- Bọc File Lock liên tiến trình an toàn, tự động tăng/reset biến đếm `consecutive_fails`.

---

## 4. Quy tắc vận hành & Bài học đúc kết
1. **Luật mềm (Prompt) luôn thua trước sức ép chữa cháy**: Mọi invariant an toàn tối thượng (`cấm bấm tay ADB`, `cấm grep diện rộng`, `cấm goal mở`) BẮT BUỘC phải có Hook code cứng chặn vật lý.
2. **Terminal Timeout**: Nâng `terminal.timeout: 600` trong `config.yaml` để các cuộc gọi thẩm định Claude CLI Opus High không bị kill giữa chừng.
3. **Async Bulkhead**: Coordinator là bộ não điều phối, không phải worker thực thi. Không bao giờ được để luồng chính Coordinator bị block bởi I/O thiết bị thật quá 60 giây.
