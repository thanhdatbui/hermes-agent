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

## 3. Kiến Trúc Chuyển Đổi SSOT SQLite Cho Chuỗi Gmail & Khắc Phục OmniRoute Timeout (2026-11-05)
- **Chuỗi Gmail Đã Thuần SQLite 100%:**
  1. *Reg Gmail (`merge_success_results.py`)*: Nạp thẳng vào `mailboxes` của `farm_master.db`.
  2. *Replication 2 chiều (`sync_2fa_to_admin.py`)*: Kéo mailboxes Admin về Kibe, đẩy mailboxes Kibe sang Admin qua mạng LAN (1.492 hòm thư khớp 100%).
  3. *Bật 2FA (`post_morning_gmail_2fa_watchdog.py`)*: Nạp mật khẩu từ SQLite `mailboxes`, fallback về Excel khi DB vắng mặt.
  4. *Đồng bộ Gmail Live (`sync_gmail_clean_v2_to_tong.py`)*: Xuất từ SQLite `mailboxes` ra `gmail_live_tong.txt`.
- **Chẩn đoán OmniRoute :20129 Timeout / Rate limit 429:**
  - Khi Gate B triệu tập Hội đồng Cố vấn (`gemini`, `sol`) bị treo tới 300s dẫn đến `PLAN_FAILED`, nguyên nhân do tài khoản trong pool bị dính `429 RESOURCE_EXHAUSTED` từ Google API khiến combo fallback quay vòng qua hàng chục model.
  - Phục hồi: Gọi POST `http://localhost:20129/api/restart` để làm sạch connection pool và kiểm tra logs qua `http://localhost:20129/api/logs/console`.

## 4. Triage Sự Cố SSH Banner Abort Sau Reboot & Fallback Remote ADB Socket (2026-11-06)
- **Bẫy suy diễn "SSH treo tiến trình":** Khi host Admin được reboot định kỳ mà kết nối SSH vẫn bị reset ngay bước bắt tay (`Software caused connection abort` / WinError 10054 / exit 255), đây KHÔNG PHẢI lỗi tiến trình tạm thời mà là lỗi tĩnh (Host Key ACLs trên `C:\ProgramData\ssh\` cần chạy `FixHostFilePermissions.ps1`, hoặc lỗi cấu hình `sshd_config`).
- **Cơ chế Fallback Remote ADB Socket (Port 5037):** Khi SSH port 22 đứt nhưng ADB daemon `192.168.110.119:5037` vẫn LIVE và nhận đủ 78 thiết bị, Coordinator kích hoạt auto-routing điều khiển thiết bị trực tiếp qua socket LAN mà không dừng toàn bộ farm.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> - Tra cứu kiến trúc chuyển đổi SSOT SQLite & xử lý timeout OmniRoute: `skill_view(name='dual-cluster-remote-summary-retrieval', file_path='references/gmail-excel-to-sqlite-ssot-migration-architecture.md')`.
> - Tra cứu xử lý lỗi SSH Banner Abort & fallback Remote ADB socket: `skill_view(name='dual-cluster-remote-summary-retrieval', file_path='references/admin-ssh-banner-abort-vs-remote-adb-socket-fallback-20261106.md')`.
