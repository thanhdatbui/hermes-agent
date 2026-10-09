# Fail-Closed 7-Day Soak & Watchdog Lifecycle Synchronization

Tài liệu quy chuẩn kiểm soát candidate an toàn cho `post_evening_gpm_login_watchdog.py` và các cron pipeline đăng nhập GPM.

---

## 1. Nguyên Tắc Fail-Closed 7-Day Soak Gate
Để chống checkpoint và bảo vệ độ trust của tài khoản Gmail trước khi đăng nhập GPM / kích hoạt OAuth:
- **Kiểm tra clean_map (`gmail_clean_v2.xlsx`)**:
  - Bắt buộc kiểm tra `created_date`.
  - Nếu `not c_date`: **Fail-closed** — từ chối ngay lập tức (`continue`) và ghi log telemetry rõ ràng (`clean_map missing created_date (fail-closed)`).
  - Nếu `(d_today - c_date).days < 7`: từ chối với telemetry log (`clean_map soak < 7 days`).
- **Kiểm tra Fallback Master Sheet (`master_gmail_manager.xlsx`)**:
  - Cột `updated_raw` (cột 14) bắt buộc phải có giá trị. Nếu rỗng: từ chối (`continue`) kèm log telemetry.
  - Phải bọc trong `try...except` khi gọi `date.fromisoformat(updated_raw[:10])`.
  - Nếu unparseable hoặc ném ngoại lệ: từ chối (`continue`) kèm log telemetry (`invalid updated_raw ... fail-closed`).
  - Nếu `(d_today - d_updated).days < 7`: từ chối (`continue`) kèm log telemetry.
- **Cấm tuyệt đối**: Để tài khoản không xác định được ngày tạo / ngày cập nhật lọt qua bộ lọc (fail-open).

---

## 2. Đồng Bộ Hóa An Toàn Lifecycle Profile GPM (Safe Lifecycle Sync)
- Trong hàm `main()` của watchdog, việc gọi `sync_gpm_profiles_lifecycle()` phải luôn được bọc trong khối bảo vệ:
  ```python
  try:
      sync_gpm_profiles_lifecycle()
  except Exception as e:
      log(f"Lỗi chạy sync_gpm_profiles_lifecycle: {e}")
  ```
- Mục đích: Đảm bảo nếu GPM Local API tạm thời offline hoặc tiến trình GPM khởi động chậm, watchdog vẫn tiếp tục chu kỳ kiểm tra hoặc xử lý an toàn mà không crash toàn bộ tiến trình cron.

---

## 3. Proxy Daily Limit & Multi-Shift Tracking
- **Giới hạn Proxy**: Mỗi proxy port chỉ được login tối đa `MAX_LOGINS_PER_PROXY = 2` acc/ngày.
- **Tránh Pre-increment Bug**: Không được tăng biến tích lũy proxy trong vòng lặp lọc candidate nếu chưa thực thi login; chỉ tăng tạm thời trong bản sao `current_run_proxy_count` để giới hạn số lượng trong batch hiện tại.
- **Quản lý Ca (Shift State)**:
  - Ghi nhận `finished_shifts` và `reported_shifts` theo mã ca (`SANG`, `TRUA`, `TOI`).
  - Đảm bảo mỗi ca chỉ báo cáo 1 lần khi hoàn thành hoặc hết khung giờ ca.
