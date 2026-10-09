# Multi-Cluster Preflight Reg Bù & Host Awareness Invariant

> **User Mandate (04/10/2026):** "Thiếu acc thì phải tự động chạy tiktok reg bù chứ???"
> Khi một cụm farm (Kibe hoặc Admin) bị thiếu tài khoản ở một Row nuôi feed, hệ thống BẮT BUỘC phải tự động kích hoạt chuỗi Preflight Reg Bù (`ensure_row_accounts.py`), nạp Hotmail/Graph API và reg TikTok bù trước giờ nuôi. CẤM chấp nhận trạng thái "0 valid accounts -> skip window" một cách thụ động.

---

## 1. Cơ chế Multi-Cluster Preflight trong `tiktok_runner.py`
Trước mỗi window nuôi feed (12:00, 14:00, 18:00, 20:00, ...):
1. Runner duyệt qua từng cụm `CLUSTERS = [kibe, admin]`.
2. Với mỗi cụm, runner gọi `_preflight_ensure_accounts(row, window_key, cluster)`:
   - Truyền `TAADAA_HOST_CONFIG` tương ứng (`kibe.yaml` hoặc `admin.yaml`).
   - Truyền `ADB_SERVER_SOCKET` nếu là remote cluster (Admin: `tcp:192.168.110.119:5037`).
   - Tạo marker file de-dup `.preflight_<cluster>_<window_key>` để chống spam trong window.
   - Chạy `python D:/Taadaa/tools/ensure_row_accounts.py <row>`.

---

## 2. Pitfall chí mạng: Host Fallback Desync trong `ensure_row_accounts.py`
- **Hiện tượng:** Cụm Admin (Máy 201-280) thiếu acc ở Row 4, nhưng watchdog báo cáo hoàn toàn không có tên FARM ADMIN, và runner ghi `Row 4 co 0 account hop le, skipping window`.
- **Nguyên nhân gốc rễ:**
  - `ensure_row_accounts.py` cần nạp `taadaa_host.py` để đọc `TAADAA_HOST_CONFIG`.
  - Nếu `D:/Taadaa/tools` không nằm trong `sys.path`, lệnh `import taadaa_host` bị `ImportError` âm thầm.
  - Hàm `get_host_info()` fallback mặc định về `HOST_ID = "kibe"`, đọc nhầm `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`.
  - Trên Kibe đã có đủ 80/80 nick -> script in `[KIBE] Row 4: Toan bo may da day du tai khoan! Khong can reg` và exit 0 ngay lập tức mà không hề kiểm tra hay reg cho Admin!
- **Khắc phục chuẩn:**
  1. Luôn đưa `D:/Taadaa/tools` vào `sys.path` trước khi `import taadaa_host`.
  2. Bổ sung env check trực tiếp: nếu `TAADAA_HOST_CONFIG` chứa `admin`, bắt buộc trỏ đúng `HOST_ID = "admin"`, `workbook_root = D:/OneDrive/TaadaaData/admin`, `runtime_root = D:/Taadaa/runtime/admin`.

---

## 3. Quy trình Triage khi Watchdog thiếu cụm Farm
Khi `feed_session_watchdog.py` báo cáo thiếu cụm Farm (ví dụ vắng bóng Admin):
1. **Kiểm tra Artifact Dir:** Xem `D:/Taadaa/runtime/<cluster>/live/<date>` có folder run hay không.
2. **Kiểm tra Runner State:** Đọc `D:/Taadaa/runtime/<cluster>/cron-state/runner_simple_state.json` xem window có bị skip do `valid_count == 0` không.
3. **Kiểm tra Preflight Reg:** Nếu `valid_count == 0`, kiểm tra ngay tại sao `ensure_row_accounts.py` không chạy reg bù cho cluster đó. Tuyệt đối không dừng lại ở kết luận "do thiếu nick".
