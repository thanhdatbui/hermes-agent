# Dual-Cluster Summary Aggregation & Remote Artifact Sync Lessons

## 1. Vấn đề Regex stdout qua SSH Sub-shell
Khi Coordinator hoặc Watchdog chạy tiến trình batch đa cụm (ví dụ: Reg Gmail hoặc TikTok 2FA qua `admin-farm` bằng SSH EncodedCommand):
- Sub-shell PowerShell trên remote host (`powershell.exe -NoProfile -File ...`) có thể output các block progress XML, lỗi CLIXML hoặc buffer stdout bị ngắt/nuốt mất dòng tóm tắt `TOTAL=... SUCCESS=... FAILED=...`.
- Kết quả: Bộ parser regex trên Coordinator/Kibe không bắt được dòng format mong đợi, dẫn đến việc cluster remote bị gán mặc định là 0 máy (dù thực tế remote đã chạy đủ 15 máy).

## 2. Giải pháp Chuẩn hóa (Direct Remote Summary Query)
Thay vì cố parse stdout stream:
1. Ghi nhận `start_epoch = datetime.now().timestamp()`.
2. Sau khi subprocess SSH kết thúc, gọi một lệnh PowerShell ngắn qua `admin_ssh.py` để query file `summary.json` có `LastWriteTime >= start_epoch`:
   ```powershell
   $min = [DateTimeOffset]::FromUnixTimeSeconds(<start_epoch>).LocalDateTime;
   $items = Get-ChildItem -Path 'D:\CodexRuntime\...\logs_parallel_*\summary.json' | Where-Object { $_.LastWriteTime -ge $min } | Sort-Object LastWriteTime -Descending;
   if ($items) { Get-Content $items[0].FullName -Raw -Encoding UTF8 }
   ```
3. Parse structured JSON từ kết quả trả về để lấy chính xác các chỉ số `total`, `success`, `failed`, `skip_safe`, `failure_breakdown`.

## 3. Khế ước Thuộc tính `StartupStep` giữa các Repo
- `automation-core/src/automation_core/startup.py` khai báo `StartupStep(action, result, error, evidence)`.
- Khi các repo vệ tinh (như `register gmail/gmail_reg_v10.py`) gọi `prepare_app_for_automation` và duyệt `step in app_startup.steps`:
  - Phải có `@property def name(self) -> str: return self.action` trên dataclass `StartupStep` để tương thích ngược.
  - Phía caller luôn bọc phòng thủ:
    ```python
    (getattr(step, "action", None) or getattr(step, "name", "")) in ("verify_app_focus", "focus_app")
    ```
  - Tránh triệt để `AttributeError` khi một trong hai host chưa kịp pull/deploy bản cập nhật mới nhất.
