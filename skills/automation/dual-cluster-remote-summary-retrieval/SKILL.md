---
name: dual-cluster-remote-summary-retrieval
description: "Kỷ luật truy vấn remote summary qua SSH PowerShell chống bẫy đọc lén log cũ và quy chuẩn môi trường thi công Farm Admin."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [dual-cluster, remote-ssh, admin-farm, powershell-allowlist, summary-aggregation, anti-phantom]
---
# Dual-Cluster Remote Summary Retrieval & Farm Admin Environment Parity

## 1. Bản chất sự cố "Báo cáo ma" (Phantom Old Summary Desync)
Khi hệ thống chạy mô hình Dual-Cluster (PC Kibe + PC Admin via SSH):
- Phía Kibe có Watchdog (`cron_night_tiktok_2fa_watchdog.py`) gom `summary.json` từ cả Kibe local và Admin remote qua SSH PowerShell.
- **Bẫy chí mạng:** Lệnh đọc remote summary nếu viết dạng:
  ```powershell
  # CẤM TUYỆT ĐỐI (DẪN ĐẾN ĐỌC LÉN LOG NGÀY HÔM TRƯỚC):
  Get-Content (Get-ChildItem -Path 'D:\CodexRuntime\...\logs_parallel_*\summary.json' | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
  ```
  Khi máy Admin gặp sự cố (mất file code, rớt SSH, mạng lag, không chạy lượt nào trong ca), lệnh trên vẫn tìm thấy thư mục log của ngày hôm trước/ca trước và trả về kết quả cũ.
  $\rightarrow$ Watchdog Kibe lấy kết quả mới của Kibe cộng với kết quả cũ của Admin, tạo ra số liệu sai lệch và che giấu hoàn toàn việc Admin đang chết đứng!

## 2. Giải pháp cơ học O(1) bắt buộc cho Watchdog Remote Query
1. **Khóa chặn `Where-Object` bằng Timestamp của ca hiện tại:**
   Lệnh PowerShell remote bắt buộc phải nhận mốc thời gian bắt đầu ca (`min_mtime`) và lọc:
   ```powershell
   Get-ChildItem -Path 'D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_*\summary.json' -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge (Get-Date '<min_date_str>') } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content -Raw -Encoding UTF8
   ```
2. **Quy tắc an toàn Allowlist của `admin_ssh.py`:**
   - Dùng cú pháp pipeline liền mạch: `Get-ChildItem ... | Where-Object ... | Sort-Object ... | Select-Object ... | Get-Content ...` (mở đầu bằng `Get-` nằm trong allowlist của `admin_ssh.py`).
   - CẤM bọc ngoài `Get-Content (...)` vì nếu không có file nào khớp `Where-Object`, biểu thức trong ngoặc trả về `$null` khiến `Get-Content` văng exception `ParameterArgumentValidationErrorNullNotAllowed`.
   - Pipeline trực tiếp sẽ trả về rỗng một cách an toàn và sạch sẽ khi Admin chưa có lượt chạy mới.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> - Tra cứu kiến trúc chuyển đổi SSOT SQLite & xử lý timeout OmniRoute: `skill_view(name='dual-cluster-remote-summary-retrieval', file_path='references/gmail-excel-to-sqlite-ssot-migration-architecture.md')`.
