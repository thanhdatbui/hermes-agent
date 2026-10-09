# Register Gmail Runner Preflight & Watchdog Triage (2026-09-24)

## 1. Phân biệt 2 Tầng Lỗi Reg Gmail (O(1) Triage)

Khi user hoặc watchdog báo lỗi "Reg Gmail bị lỗi", Coordinator phải kiểm tra ngay tại thư mục runtime `D:\CodexRuntime\codex_gmail_debug-register-gmail` để phân loại:

### Tầng 1: Device / Account Execution Failure (Bình thường)
- **Dấu hiệu**: Có thư mục `logs_parallel_<YYYYMMDD_HHMMSS>` mới được tạo, có `summary.json`.
- **Bản chất**: Runner khởi động thành công, tuyển chọn được danh sách máy (ví dụ 15 máy). Thất bại xảy ra trên thiết bị thật:
  - `PHONE_VERIFY`: Google yêu cầu số điện thoại (checkpoint).
  - `ACCOUNT_CREATION_ERROR`: Google từ chối tạo tài khoản.
  - `DEVICE_NOT_FOUND` / `OFFLINE`: Mất kết nối ADB.
- **Hành động**: Đọc `summary.json` và log từng máy `machine_<STT>.log`. Không đụng vào runner logic.

### Tầng 2: Preflight Launcher Crash ("LỖI KHỞI ĐỘNG RUNNER", Exit Code 1, Tổng máy: 0)
- **Dấu hiệu**: 
  - Watchdog báo: `Phase 1 (Reg Gmail - Code 1): LỖI KHỞI ĐỘNG RUNNER (Tổng máy: 0, Success: 0, Fail: 0)`.
  - Không có thư mục `logs_parallel_*` mới.
  - Không có file `lock_scope_audit_*.json` mới.
- **Bản chất**: PowerShell script (`run_all.ps1` -> `run_parallel.ps1`) bị `throw` hoặc `exit 1` ngay trong các bước kiểm tra điều kiện tiên quyết (Preflight) TRƯỚC dòng 545, chưa spawn bất kỳ worker nào.

---

## 2. Pitfall: Watchdog Nuốt Stderr/Stdout Khi Preflight Lỗi
- Trong `post_noon_chain_watchdog.py`:
  - `run_gmail_batch()` chạy `subprocess.run(capture_output=True)`.
  - `parse_summary_counts()` chỉ regex tìm `TOTAL=...` hoặc đọc `summary.json`.
  - Khi PowerShell throw exception, output lỗi nằm trong `proc.stdout + proc.stderr`. Nhưng watchdog chỉ format string `LỖI KHỞI ĐỘNG RUNNER` mà **không in `g_out` ra stdout hay gửi Telegram**.
  - **Hệ quả**: Báo cáo cụt ngủn `Code 1: 0 máy`, gây hoang mang tưởng nhầm tài khoản bị lỗi diện rộng.

---

## 3. Checklist Khoanh Vùng Preflight Trực Tiếp (Trước Dòng 545 `run_parallel.ps1`)

Kiểm tra theo thứ tự $O(1)$ không can thiệp thiết bị:

1. **Kiểm tra Phân quyền Target (`AssignmentManifest`)**:
   - `run_parallel.ps1` dòng 523:
     `if (-not $assignmentManifest -or -not $workerId) { throw "Set GMAIL_ASSIGNMENT_MANIFEST and GMAIL_WORKER_ID..." }`
   - Manifest: `C:\Users\Kibe\AppData\Local\automation-core\assignments\register-gmail.json`.
   - Worker ID: `taadaa-writer-3c47f89f35e44795a79267e09fbcc72d`.
   - Đảm bảo biến môi trường `GMAIL_ASSIGNMENT_MANIFEST` và `GMAIL_WORKER_ID` không bị rỗng.

2. **Kiểm tra Device Inventory & Proxy Mapping**:
   - `run_all.ps1` gọi `gmail_reg_v10.load_device_map_from_excel()`.
   - Nguồn đọc: `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` (hoặc `kibe\PROXYgandienthoai.xlsx`).
   - Đảm bảo file Excel không bị process khác khóa độc quyền (lock sharing violation).

3. **Kiểm tra Cooldown & Ready Filter**:
   - `run_parallel.ps1` gọi `gmail_reg_v10.get_machines_ready(min_days, quiet=True)`.
   - Đọc `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
   - Nếu không có máy nào đủ cooldown ($\ge 5$ ngày): Script thoát an toàn với `exit 0` (không phải Code 1).
   - Nếu đọc Excel lỗi: raise exception -> `exit 1`.

4. **Kiểm tra Xung Đột Khóa Thiết Bị (`Device Locks`)**:
   - Kiểm tra `C:\Users\Kibe\.codex\device-locks`: Nếu ca trước (ví dụ ca trưa) chưa dọn lock hoặc tiến trình khác đang claim máy, số máy còn lại sau lock probe có thể bị rỗng.

---

## 4. Kỷ Luật Điều Phối Coordinator
- **CẤM TUYỆT ĐỐI**: Tự chạy `run_all.ps1` hoặc `run_parallel.ps1` từ terminal chính để "thử xem lỗi gì". Lệnh này sẽ kích hoạt batch trên toàn bộ điện thoại thật của farm!
- **ĐÚNG**: Dispatch worker subagent tái hiện riêng biệt khối preflight python/powershell với cờ dry-run hoặc kiểm tra từng module cô lập.
