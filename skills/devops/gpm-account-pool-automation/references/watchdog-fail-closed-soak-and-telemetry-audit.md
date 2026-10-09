# Watchdog Fail-Closed 7-Day Soak & Telemetry Audit Patterns

## 1. Fail-Closed Validation for 7-Day Account Aging (Soak Gate)
Khi lọc Gmail từ `clean_map` (hoặc các file nguồn đăng ký sạch / `gmail_clean_v2.xlsx`), nếu thông tin ngày tạo (`created_date`) bị thiếu (`None`) hoặc không parse được:
- **Nguyên tắc an toàn (Fail-Closed):** Tuyệt đối KHÔNG bỏ qua kiểm tra hoặc cho phép đi tiếp. Nếu `created_date is None` hoặc `(today - created_date).days < 7`, bắt buộc phải loại bỏ (`continue`) ngay lập tức.
- **Rủi ro nếu fail-open:** Các tài khoản mới tạo chưa đủ độ trễ trust 7 ngày sẽ bị đưa vào login GPM / OAuth dẫn đến Google kích hoạt checkpoint thiết bị hoặc khóa tài khoản hàng loạt.

```python
if em_l in clean_map:
    info = clean_map[em_l]
    c_date = info.get("created_date")
    if not c_date:
        filtered_soak += 1
        continue
    if (d_today - c_date).days < 7:
        filtered_soak += 1
        continue
```

## 2. Defensive Lifecycle Sync Invocation in Watchdog Runs
- Ngay cả khi có cron riêng (`sync_gpm_lifecycle.py`) đảm nhiệm việc tạo và dọn profile rác, watchdog ca chạy (sáng/trưa/tối) vẫn nên bọc lệnh gọi `sync_gpm_profiles_lifecycle()` trong `try...except` phòng vệ.
- Điều này đảm bảo:
  - Nếu GPM API offline hoặc gặp lỗi tạm thời, watchdog vẫn tiếp tục xử lý các candidate sẵn có mà không crash toàn bộ tiến trình.
  - Profile DIE / BAN được dọn kịp thời trước khi watchdog phân bổ lượt login.

## 3. Telemetry & Observability in Candidate Pipeline
Để tránh "chạy mù" và dễ dàng kiểm toán (audit):
- Luôn thu thập các chỉ số đếm phân loại:
  - `total_parsed`: Tổng số dòng / tài khoản duyệt qua.
  - `filtered_soak`: Số tài khoản bị loại do chưa đủ 7 ngày hoặc thiếu ngày tạo.
  - `filtered_proxy_limit`: Số tài khoản bị chặn vì proxy đã chạm trần (`MAX_LOGINS_PER_PROXY`).
  - `selected_candidates`: Phân bổ theo mức ưu tiên (`P1` Google session sẵn, `P2` ChatGPT trust bồi, `P3` thường).
- Log telemetry dạng structured một dòng trước khi dispatch pool worker:
  `[CANDIDATES-TELEMETRY] Parsed: X | Filtered soak (<7d/invalid): Y | Filtered proxy-limit: Z | Selected: W (P1=..., P2=..., P3=...)`
