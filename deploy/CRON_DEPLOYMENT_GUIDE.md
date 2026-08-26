# HƯỚNG DẪN ĐỒNG BỘ CẤU HÌNH CRON & SCRIPTS (MULTI-MACHINE DEPLOYMENT)

Tài liệu này hướng dẫn vị trí lưu trữ và cách triển khai danh mục **Hermes Cron Jobs** và **Scripts** từ repo `D:\Taadaa\Hermes` sang các máy trong Farm (máy chính Kibe hoặc máy phụ Admin).

---

## 1. Cấu trúc lưu trữ trong Repo

Tất cả cấu hình và mã nguồn Cron phục vụ farm được quản lý tập trung tại:

```text
D:\Taadaa\Hermes\deploy\hermes-home\
├── cron\
│   └── jobs.json             ← Danh sách 14 Cron Jobs chuẩn (lịch chạy, cấu hình no_agent, workdir, model...)
└── scripts\                  ← Toàn bộ script Python chạy định kỳ (.py)
    ├── tiktok_runner.py
    ├── tiktok_watcher.py
    ├── tiktok_picker.py
    ├── watch_device_locks.py
    ├── reap-dead-owner-locks-wrapper.py
    ├── feed_session_watchdog.py
    ├── tik4_render_watchdog.py
    ├── daily_manual_stock_checklive.py
    ├── cron_clear_tiktok_cache.py
    └── ... (các script hỗ trợ khác)
```

---

## 2. Đường dẫn Runtime trên từng Máy Windows

Khi Hermes chạy, hệ thống sẽ đọc cấu hình và script từ thư mục người dùng:

| Thành phần | Đường dẫn Runtime | Mô tả |
|---|---|---|
| **Cron Config** | `%LOCALAPPDATA%\hermes\cron\jobs.json` | Chứa danh sách tác vụ cron đang active |
| **Cron Scripts** | `%LOCALAPPDATA%\hermes\scripts\` | Nơi chứa các file script được gọi từ `jobs.json` |
| **Lịch sử chạy** | `%LOCALAPPDATA%\hermes\cron\executions.db` | Database SQLite ghi log thực thi (không commit) |

---

## 3. Quy trình Triển khai sang Máy Mới / Máy Admin

Khi cài đặt máy Admin (hoặc sau khi cập nhật Cron mới trên repo):

### Bước 1: Pull cập nhật mới nhất từ Repo
```powershell
cd D:\Taadaa\Hermes
git pull --rebase origin main
```

### Bước 2: Đồng bộ Cron & Scripts vào Hermes Runtime
Chạy lệnh PowerShell sau để copy toàn bộ cấu hình Cron và Scripts vào `%LOCALAPPDATA%\hermes\`:

```powershell
# Copy scripts
$scriptsSrc = "D:\Taadaa\Hermes\deploy\hermes-home\scripts"
$scriptsDst = "$env:LOCALAPPDATA\hermes\scripts"
New-Item -ItemType Directory -Force -Path $scriptsDst | Out-Null
robocopy $scriptsSrc $scriptsDst *.py /xo

# Copy cron jobs configuration (nếu máy mới chưa có hoặc cần áp dụng mẫu)
$cronSrc = "D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json"
$cronDst = "$env:LOCALAPPDATA\hermes\cron\jobs.json"
New-Item -ItemType Directory -Force -Path "$env:LOCALAPPDATA\hermes\cron" | Out-Null
if (-not (Test-Path $cronDst)) {
    Copy-Item $cronSrc $cronDst -Force
    Write-Host "Đã khởi tạo jobs.json cho máy mới."
} else {
    Write-Host "File jobs.json đã tồn tại. Nếu muốn ghi đè cấu hình mẫu, dùng: Copy-Item '$cronSrc' '$cronDst' -Force"
}
```

### Bước 3: Kiểm tra danh sách Cron sau khi nạp
```powershell
hermes cron list
```
Tất cả các Cron job (Feed, Watcher, Watchdog, Dọn lock, Render, ...) sẽ hiển thị đầy đủ và tự động kích hoạt theo lịch.
