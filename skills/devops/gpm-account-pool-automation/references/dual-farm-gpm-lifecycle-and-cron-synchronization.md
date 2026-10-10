# Dual-Farm GPM Lifecycle & Cron Synchronization Runbook (Kibe & Admin)

## 1. Nguyên Tắc Bất Biến Dual-Farm (Dual-Farm Invariant)
- **Quy tắc cốt lõi:** Toàn bộ hệ thống Phone Farm gồm 2 cụm:
  * **Farm Kibe:** Máy 1 – 80 (hỗn hợp Gmail và Hotmail).
  * **Farm Admin:** Máy 201 – 280 (100% Hotmail, 0 Gmail).
- **Yêu cầu điều phối:** Mọi cronjob vòng đời, supervisor, watchdog và báo cáo tổng kết **BẮT BUỘC phải chạy song hành cho CẢ 2 FARM**. Tuyệt đối không được hardcode chỉ chạy Kibe mà bỏ rơi Admin.

---

## 2. Phân Vùng Dữ Liệu & Cấu Hình Độc Lập

| Thông số / Thành phần | Farm Kibe (M1-80) | Farm Admin (M201-280) |
| :--- | :--- | :--- |
| **Thư mục dữ liệu** | `D:\OneDrive\TaadaaData\kibe` | `D:\OneDrive\TaadaaData\admin` |
| **Master Workbook** | `taikhoan_dat_v2_updated .xlsx` (12 cột) | `taikhoan_dat_v2_updated .xlsx` (10-11 cột) |
| **Proxy Workbook** | `PROXYgandienthoai.xlsx` | `PROXYgandienthoai.xlsx` |
| **Thư mục State** | `D:\Taadaa\runtime\kibe\cron-state` | `D:\Taadaa\runtime\admin\cron-state` |
| **Supervisor Wrapper** | `gpm_5profiles_supervisor_wrapper.py` | `gpm_5profiles_supervisor_admin_wrapper.py` |
| **Lịch Cron Supervisor** | `*/5 * * * *` (phút 0, 5, 10, 15...) | `2,7,12,17... * * * *` (lệch 2 phút) |

---

## 3. Các Điểm Nghẽn Kỹ Thuật & Giải Pháp (Hard-Won Lessons)

### A. Lệch Cột Excel giữa 2 Farm (IndexError in `load_accounts`)
- **Triệu chứng:** Khi supervisor chạy trên file Admin bị văng lỗi:
  ```text
  IndexError: tuple index out of range at "chatgpt_password": str(row[col.get("PASS CHATGPT", 11)]...)
  ```
- **Nguyên nhân:** File Excel của Admin khuyết cột 11 (`PASS CHATGPT`), hàng chỉ có 10 phần tử.
- **Giải pháp:** Sử dụng helper đọc cell an toàn có kiểm tra độ dài hàng:
  ```python
  def _cell(col_name: str, fallback_idx: int) -> str:
      idx = col.get(col_name, fallback_idx)
      return str(row[idx] or "").strip() if (idx is not None and idx < len(row)) else ""
  ```

### B. Kế Thừa Môi Trường Subprocess (Subprocess Env Inheritance)
- **Triệu chứng:** Supervisor chạy đúng env Admin nhưng khi gọi `CHANGE_INFO` (`gpm_change_hotmail_security.py`) thì script con lại quay về đọc file Kibe.
- **Nguyên nhân:** Hàm `run_cmd` trong supervisor gọi `subprocess.run(argv)` mà không truyền `env=env`, làm mất các biến môi trường `GPM_SUPERVISOR_*`.
- **Giải pháp:** Bắt buộc truyền `env = os.environ.copy()` vào `subprocess.run(argv, env=env, ...)`. Đồng thời trong `gpm_change_hotmail_security.py` đọc đường dẫn qua `os.environ.get("GPM_SUPERVISOR_ACCOUNT_XLSX")` và `os.environ.get("GPM_SUPERVISOR_DATA_DIR")`.

### C. Giảm Tải Concurrency GPMLogin (Staggered Scheduling)
- Để tránh 2 tiến trình supervisor Kibe và Admin cùng lúc gọi GPM API (port 19995) gây nghẽn driver hoặc spike CPU/RAM:
  * Cron Kibe: Chạy vào các phút `0, 5, 10, 15, 20...`
  * Cron Admin: Chạy vào các phút `2, 7, 12, 17, 22...` (so le 2 phút).

### D. Đồng Bộ Báo Cáo 6H (`cron_hotmail_gpm_lifecycle_6h_report.py`)
- Script báo cáo BẮT BUỘC nạp state từ cả 2 file:
  * `KIBE_STATE_PATH = Path("D:/Taadaa/runtime/kibe/cron-state/batch_gpm_5profiles_supervisor_state.json")`
  * `ADMIN_STATE_PATH = Path("D:/Taadaa/runtime/admin/cron-state/batch_gpm_5profiles_supervisor_state.json")`
- Xuất số liệu tổng thể toàn Farm (ví dụ: Tổng 1.035 acc: Kibe 418 | Admin 617) và phân rã chi tiết từng cụm.

### E. Kỷ Luật Cách Ly Proxy Farm
- IP Mikrotik PPPoE (`10001 - 10040`) là IP dành riêng cho các thiết bị Android của farm. CẤM TUYỆT ĐỐI mượn IP này để chạy login tự do bên ngoài nếu không phải là profile của chính tài khoản trên máy đó.
