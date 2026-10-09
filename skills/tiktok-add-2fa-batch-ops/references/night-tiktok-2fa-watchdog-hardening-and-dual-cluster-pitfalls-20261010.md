# Night TikTok 2FA Watchdog Hardening & Dual-Cluster Pitfalls (10/10/2026)

Tài liệu đúc kết từ sự cố watchdog ban đêm `night-tiktok-2fa-watchdog` và quy chuẩn vận hành 2FA hai cụm (Kibe M1-80 & Admin M201-280).

---

## 1. Sự cố NameError / UnboundLocalError trong Dual-Cluster Summary
- **Hiện tượng:** Watchdog ban đêm gọi subprocess chạy cả hai cụm Kibe và Admin. Output trả về chứa `=== CLUSTER ADMIN` kích hoạt nhánh rẽ `if "=== CLUSTER ADMIN" in out:`.
- **Bẫy code cũ:** Hai biến `suc` và `fail` chỉ được gán trong nhánh `else:` của single-cluster. Khi vào nhánh dual-cluster, lúc gọi `save_state` ở cuối script, Python văng lỗi:
  ```text
  UnboundLocalError: cannot access local variable 'suc' where it is not associated with a value
  ```
  khiến tiến trình thoát với exit code 1 và kích hoạt cảnh báo cron thất bại.
- **Quy chuẩn sửa đổi:** Bắt buộc tính toán tổng số máy hoàn tất và lỗi tường minh cho cả hai nhánh:
  ```python
  suc = k_res["success"] + a_res["success"]
  fail = k_res["failed"] + a_res["failed"]
  ```

---

## 2. Chuẩn hóa Return Code của Watchdog & Runner
- **Quy ước Return Code của `run_batch_live_2fa.py`:**
  - `0` (`EXIT_SUCCESS`): Tất cả máy mục tiêu hoàn tất kích hoạt 2FA thành công.
  - `4` (`EXIT_SAFE_SKIP`): Không có máy nào cần chạy (toàn bộ đã có 2FA hoặc an toàn bỏ qua nhường tác vụ khác).
  - Khác 0 và 4: Lỗi thực thi / timeout.
- **Quy tắc Exit Code của Watchdog (`main()`):**
  - Không được `return 0` mù quáng khi có lỗi.
  - Nếu runner trả code không nằm trong `ACCEPTABLE_RETURN_CODES = (0, 4)` ➔ return code lỗi (hoặc 1).
  - Nếu có máy lỗi (`fail > 0`) ➔ return 1 để cron scheduler và monitoring phát hiện sự cố.
  - Chỉ return 0 khi chạy hoàn tất sạch sẽ (`code in (0, 4)` và `fail == 0`).

---

## 3. Quản trị Cấu hình Môi trường (Config Portability)
- Không hard-code tuyệt đối các đường dẫn Windows (`D:/Taadaa`, `C:/Users/Kibe`, `D:/OneDrive/...`).
- Bắt buộc bọc fallback qua biến môi trường để dễ dàng tái sử dụng và kiểm thử:
  - `TAADAA_TIKTOK_2FA_REPO`: Mặc định `D:/Taadaa/tiktok-add-bao-mat-f2a`
  - `TAADAA_KIBE_WORKBOOK`: Mặc định `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`
  - `TAADAA_ADMIN_SSH`: Mặc định `admin-farm`
  - `TAADAA_ADB_PATH`: Mặc định `C:\Program Files (x86)\xiaowei\tools\adb.exe`
- Bổ sung `correlation_id` (uuid4 hex ngắn) trong mỗi phiên chạy để theo dõi log và state đồng bộ.
