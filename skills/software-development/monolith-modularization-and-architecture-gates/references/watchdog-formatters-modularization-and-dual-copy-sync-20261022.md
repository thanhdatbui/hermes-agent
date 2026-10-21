# Watchdog Formatters Modularization and Dual-Copy Byte Sync Parity (2026-10-22)

## Context & Incident
Trong ca trực sáng 2026-10-22, một agent (Luna) đã commit logic đếm follow thành công vào `scripts/feed_session_watchdog.py`, đẩy kích thước file lên 1.484 dòng, vượt qua ngân sách trần cứng $\le 1.450$ dòng và làm fail bài test kiến trúc `test_watchdog_architecture_gate.py`.
Đồng thời, bản sao `scripts/hermes_cron/feed_session_watchdog.py` bị lệch nội dung, vi phạm bài test đối soát byte-for-byte `test_feed_session_watchdog_and_hermes_cron_sync`.

## Key Invariants & Rules

### 1. Dual-Copy Byte-for-Byte Synchronization Invariant
Trong repository `tiktok-luot nuoi acc`:
- `scripts/feed_session_watchdog.py` (file gốc) và `scripts/hermes_cron/feed_session_watchdog.py` (file cron mirror) BẮT BUỘC phải đồng bộ 100% từng byte:
  ```python
  with open(p1, "rb") as f1, open(p2, "rb") as f2:
      assert f1.read() == f2.read(), "feed_session_watchdog must be synchronized with hermes_cron mirror"
  ```
- Bất kỳ thay đổi nào trên một file BẮT BUỘC phải đồng bộ sang file kia trước khi chạy test và commit.

### 2. Architecture Line Budget Invariant (<= 1450 lines)
- Ngân sách dòng của `scripts/feed_session_watchdog.py` bị khóa cứng tại 1.450 dòng qua `test_feed_session_watchdog_line_budget`.
- Khi cần bổ sung logic format báo cáo Telegram, phân loại hoặc cảnh báo, CẤM thêm trực tiếp vào file chính. BẮT BUỘC bóc tách sang subpackage `scripts/watchdog/`:
  - `scripts/watchdog/formatters.py`: Format báo cáo follow (`format_follow_report_from_blocks`, `dispatch_split_reports`, `format_success_follows`, `format_released_follows`).
  - `scripts/watchdog/alerts.py`: Định nghĩa ngưỡng `DEFAULT_FARM_ALERT_THRESHOLD`, starvation metrics, alert triggers.
  - `scripts/watchdog/merger.py`: Merge kết quả giữa các lượt chạy.
  - `scripts/watchdog/lock.py`: Quản lý tiến trình và device locks.
  - `scripts/watchdog/parser.py`: Trích xuất kết quả từ runtime artifacts.

### 3. Fallback Import & NameError Shielding trong Subpackages
Khi bóc tách hàm sang `scripts/watchdog/formatters.py`, các hằng số liên quan từ module anh em (như `alerts.py`) phải được import có fallback an toàn để tránh `NameError`:
```python
try:
    from .alerts import DEFAULT_FARM_ALERT_THRESHOLD
except ImportError:
    try:
        from scripts.watchdog.alerts import DEFAULT_FARM_ALERT_THRESHOLD
    except ImportError:
        DEFAULT_FARM_ALERT_THRESHOLD = 8
```

### 4. Dispatch Worker Automation Protocol
- Để thực thi bóc tách mã nguồn O(1) an toàn mà không làm bẩn context Coordinator:
  Sử dụng `claude_worker.py --file <path> --workdir <dir> "<prompt>"` thay vì chạy các script có model override chưa được catalog nhận diện.
- Sau khi worker hoàn tất, Coordinator nghiệm thu ngay bằng lệnh test tập trung:
  ```bash
  pytest tests/test_watchdog_architecture_gate.py python_runner/tests/test_follow_session_watchdog.py
  ```
