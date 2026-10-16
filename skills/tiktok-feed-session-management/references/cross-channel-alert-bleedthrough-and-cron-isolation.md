# Cross-Channel Alert Bleed-Through & Watchdog Modularization Invariants

## 1. Ngăn chặn triệt để Cross-Channel Alert Bleed-Through (Lẫn lộn Farm Alert chéo kênh)

### Hiện tượng lỗi (Bug Pattern):
Người dùng đã yêu cầu tách độc lập 3 kênh báo cáo Telegram:
1. `tiktok luot nuoi acc` (`-5377611430`): Báo cáo Lướt Feed.
2. `tiktok follow` (`-5127276494`): Báo cáo Follow chéo.
3. `tiktok video` (`-5435853713`): Báo cáo Đăng Video.

Tuy nhiên, trong `feed_session_watchdog.py`, nhánh mặc định `mode == "feed"` (chạy cho cronjob Feed) lại vẫn tính toán tổng lỗi Follow (`tot_fl_err`) và tổng lỗi Upload (`tot_up_err`). Khi Follow hoặc Upload gặp lỗi hàng loạt ($\ge 8$ máy):
```python
# CODE SAI PHẠM (REGRESSION TRAP):
tot_fl_err = sum(len(b.get("fl_error", [])) for b in cluster_stats)
tot_up_err = sum(len(b.get("up_error", [])) + len(b.get("up_timeout", [])) for b in cluster_stats)
has_script_alert, alert_reasons = should_trigger_farm_alert(tot_fl_err, tot_up_err, DEFAULT_FARM_ALERT_THRESHOLD)

if mode == "follow":
    msg = format_follow_report_from_blocks(...)
else:
    if has_script_alert:
        header = f"🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT ({', '.join(alert_reasons)}) - {win['name']} (Row {active_row})"
    else:
        header = f"📊 [TIKTOK NUÔI ACC] {win['name']} hoàn tất (Row {active_row})"
```
Hậu quả: Lỗi của Follow bị biến thành tiêu đề `🚨 [FARM ALERT]` và xả thẳng vào nhóm Lướt Feed (`tiktok luot nuoi acc`), gây spam rác cảnh báo vào sai nhóm dù User đã từng chỉ đạo bóc tách riêng.

### Quy tắc bất biến (Isolation Invariant):
1. **Feed Watchdog chỉ kiểm tra lỗi Feed**: Trong chế độ `mode == "feed"`, `has_script_alert` CHỈ ĐƯỢC PHÉP dựa trên lỗi của chính tiến trình Feed (`feed_error` hoặc lỗi kết nối máy). TUYỆT ĐỐI KHÔNG dùng `tot_fl_err` hay `tot_up_err` để đổi header báo cáo Feed thành `[FARM ALERT]`.
2. **Follow Alert chỉ gửi vào kênh Follow**: Báo cáo hoặc cảnh báo lỗi script Follow hàng loạt ($\ge 8$ máy) ĐỘC QUYỀN do `follow_session_watchdog.py` phụ trách và gửi về channel `-5127276494`.
3. **Upload Alert chỉ gửi vào kênh Video**: Cảnh báo upload lỗi hàng loạt chỉ gửi về channel `-5435853713` qua khối payload upload riêng.

---

## 2. Watchdog Modularization & Cron Working Directory Invariants

### Hiện tượng vỡ Cron sau khi bóc tách Monolith:
- Khi bóc tách monolith `feed_session_watchdog.py` thành package con `scripts/watchdog/{lock, alerts, merger, formatters, parser}.py`:
- Nếu dùng import tương đối dạng `from watchdog.lock import ...` hoặc `from scripts.watchdog.lock import ...`:
  - Khi script chạy từ cronjob Hermes hoặc từ thư mục khác mà không có `sys.path.insert(0, scripts_dir)`, tiến trình sẽ quăng lỗi ngay:
    `ImportError: No module named 'watchdog'`
  - Cronjob `no_agent: true` bắt `stderr` non-empty và gửi cảnh báo `⚠️ Cron failed: Script exited with code 1` spam liên tục vào Telegram của User.

### Quy tắc bất biến khi Modularize:
1. **Dynamic sys.path Injection**: BẮT BUỘC ở đầu file script phải có đoạn code tự bổ sung thư mục chứa package vào `sys.path` trước mọi câu lệnh `import watchdog.*`:
   ```python
   import os, sys
   _SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
   if _SCRIPTS_DIR not in sys.path:
       sys.path.insert(0, _SCRIPTS_DIR)
   ```
2. **Cấu hình Workdir trong Hermes Cron (`jobs.json`)**:
   Mọi cronjob gọi script phụ thuộc package cục bộ (như `feed_session_watchdog.py`, `follow_session_watchdog.py`) BẮT BUỘC phải khai báo rõ `workdir: "D:\\Taadaa\\tiktok-luot nuoi acc\\scripts"`, không được để `workdir: null`.
3. **Đồng bộ song song giữa các bản sao**:
   Nếu trong repo có các bản sao hỗ trợ như `scripts/hermes_cron/feed_session_watchdog.py` hoặc `%LOCALAPPDATA%/hermes/scripts/`, khi bóc tách package BẮT BUỘC phải đồng bộ cả package `watchdog/` hoặc tạo fallback import an toàn để tránh lệch pha giữa các môi trường thực thi.
