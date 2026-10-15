# Circuit Breaker Dashboard Filtering, Defensive Datetime Parsing & Watchdog Reload

## Bối Cảnh Sự Cố & Vấn Đề
Khi kiểm tra Dashboard `:1905` (widget **⚡ Cầu Dao Tự Ngắt IP (Circuit Breakers Tripped)**), người dùng thấy bảng vẫn hiển thị các proxy bị ngắt từ ngày 10/10 với số lượng lên tới 30 proxy, mặc dù quy tắc vận hành là cầu dao chỉ ngắt 48h rolling (đến ngày 12/10 là đã hết hạn và thực tế trên farm các máy vẫn chạy bình thường).

### Nguyên Nhân Gốc (Root Cause)
1. **Thiếu Bộ Lọc Thời Gian Trong Query**: Trong `follow_health_helper.py` (`get_follow_health_data`), câu lệnh SQL ban đầu là:
   ```sql
   SELECT proxy_key, status, tripped_by_machine, tripped_by_user, tripped_at, reset_at, target_date, saved_machines
   FROM ip_circuit_breaker
   ORDER BY tripped_at DESC
   LIMIT 30
   ```
   Do dàn farm các ngày sau chạy êm (chỉ phát sinh 4 proxy bị ngắt vào ngày 15/10), top 30 bản ghi gần nhất kéo theo 26 bản ghi cũ từ ngày 10/10 lên giao diện.
2. **Bộ Nhớ Tiến Trình Nền (Daemon In-Memory Caching)**: Khi sửa code trong `follow_health_helper.py`, process `tiktok_dashboard.py` chạy ngầm trên port 1905 đã load module vào RAM từ trước nên không tự cập nhật code mới nếu không được restart.

---

## Kiến Trúc Bản Vá Chuẩn Production (Production-Grade Invariants)

### 1. SQL Pre-Filter & Defensive Parsing
SQLite lưu cột thời gian dưới dạng `TEXT`. String comparison trực tiếp (`reset_at > ?`) trong SQL rất dễ sai âm thầm nếu dữ liệu có format khác nhau (dấu cách vs `T`, timezone, epoch, hoặc NULL).
- **SQL Pre-filter**: Lọc sơ bộ `WHERE status = 'TRIPPED'` để giảm tải đọc I/O.
- **Defensive Python Parsing**:
  ```python
  clean_ts = reset_raw.replace("T", " ")[:19]
  reset_dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=HCMC)
  ```
- **Fail-Closed Policy**: Nếu `reset_at` bị `NULL`, rỗng, hoặc không thể parse (malformed date) trên một bản ghi mang trạng thái `TRIPPED`, hệ thống **BẮT BUỘC giữ lại trong danh sách active** (fail-closed an toàn) thay vì loại bỏ âm thầm, đồng thời ghi `logger.warning(...)`.

### 2. Telemetry & Metrics Đầy Đủ
Không chỉ đếm các bản ghi lọt vào danh sách hiển thị (bị chặn trần 30), telemetry trả về phải phản ánh đầy đủ:
- `circuit_breakers_active`: Tổng số proxy đang ngắt thực tế (không bị giới hạn bởi cap 30).
- `circuit_breakers_displayed`: Số lượng bản ghi đưa vào payload hiển thị (tối đa 30).
- `circuit_breakers_filtered`: Số lượng bản ghi `TRIPPED` nhưng đã hết hạn (`reset_dt <= now`).

### 3. Khởi Động Lại Service Khi Cập Nhật Dashboard
Khi sửa logic hoặc helper của Dashboard :1905:
- Dùng `taskkill -F -PID <pid>` để tắt tiến trình `python.exe` / `pythonw.exe` cũ của dashboard.
- Watchdog ngầm `tiktok_dashboard_watchdog.ps1` (chạy mỗi 60s) sẽ tự động phát hiện cổng 1905 mất kết nối và kích hoạt `start_tiktok_dashboard_hidden.vbs` để nạp code mới trong vòng vài giây.
- Luôn kiểm tra lại endpoint API (`http://127.0.0.1:1905/api/follow-health`) và dùng `browser_vision` / WinRT OCR soi mắt kiểm chứng thực tế giao diện sau khi reload.
