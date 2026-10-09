# Gateway Restart Runtime-Sync Pitfall & Stale Lock Recovery (03/10/2026)

## 1. Hiện tượng & Triệu chứng
- Kích hoạt restart Hermes Gateway (qua delayed-restart hoặc lệnh restart gateway), nhưng Gateway không lên lại.
- Watchdog restart liên tục mỗi 2 phút nhưng đều thất bại.
- Telegram Bot im lặng hoàn toàn, không có request nào được gửi tới LLM / OmniRoute.
- Log chẩn đoán ghi nhận lỗi ImportError (ví dụ: `ImportError: cannot import name 'AuxiliaryExplicitCancellation' from 'hermes_state_common'`).

## 2. Nguyên nhân gốc rễ
1. **Runtime Skew (Đồng bộ lệch pha giữa git repo và site-packages):**
   - Khi agent sửa code hoặc copy chắp vá một vài file mới vào venv site-packages mà không đồng bộ các module phụ thuộc mới được thêm vào ở git HEAD.
   - Tiến trình Gateway cũ đang chạy ngậm trong RAM từ nhiều ngày trước vẫn dùng các bytecode cũ nên không bị ảnh hưởng.
   - Khi restart Gateway, tiến trình mới import các file vừa bị copy chắp vá và crash ngay lập tức trong quá trình bootstrap.
2. **Kẹt File Lock Mồ Côi:**
   - Khi Gateway hoặc watchdog crash liên tục, các tiến trình Python mồ côi (orphaned processes) vẫn ngậm handle khóa file state/phase lock trong Windows kernel.
   - Khi agent mới cố chạy bất kỳ tool call nào, hook điều phối an toàn không giành được lock sau 3 giây và kích hoạt cơ chế fail-closed (chặn đứng mọi tool call).
   - Điều này tạo ra trạng thái Deadlock hoàn toàn cho Agent.

## 3. Quy trình Khắc phục Chuẩn hóa

### Bước 1: Dọn sạch Tiến trình Mồ côi & Mở Khóa File Lock
Chạy PowerShell dọn dẹp các tiến trình Python mồ côi (giữ lại Gateway chính và Dashboard) và xóa file lock kẹt:
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -notlike "*gateway*run*" -and $_.CommandLine -notlike "*tiktok_dashboard*" } | Stop-Process -Force
```

### Bước 2: Đồng bộ Toàn diện Runtime từ Git HEAD
Tuyệt đối KHÔNG copy lẻ tẻ từng file module vào site-packages. Phải đồng bộ toàn bộ cây runtime từ checkout sạch của git:
1. Tạo backup thư mục site-packages hiện tại (ví dụ: `hermes\backups\sitepkg_full_<date>`).
2. Sync toàn bộ các package cốt lõi từ git HEAD vào venv site-packages:
   - `agent`, `gateway`, `hermes_cli`, `tools`, `plugins`, `providers`, `cron`, `acp_adapter`, `tui_gateway`.
   - Các module top-level mới.
3. Pre-flight test import độc lập trước khi restart daemon:
   ```bash
   python -m hermes_cli.main --help
   python -c "import gateway.platforms.telegram; print('Telegram adapter import OK')"
   ```

### Bước 3: Khởi động lại Gateway an toàn
Sau khi pre-flight test import trả về exit code 0, mới kích hoạt restart Gateway qua delayed-restart script:
Kiểm tra log trạng thái xác nhận `GATEWAY_READY` và `Connected to Telegram (polling mode)`.
